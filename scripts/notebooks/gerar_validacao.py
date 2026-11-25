import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "validacao_campos.ipynb"
JC = Path(__file__).with_name("comentarios_validacao.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Validação dos campos extraídos por regras

O código lê cada anúncio e tenta extrair, por regras, a **recompensa**, a **nação**, a **idade**, o **sexo** e as **marcas no corpo**.
Este caderno mede se essas regras acertam, comparando com uma amostra de anúncios **rotulados à mão** (`tests/fixtures/campos_gold.json`).
Campos `{config.VERSAO_CAMPOS}`. O caderno **não lê o banco**: só o arquivo de rótulos e o código local.

- **Precisão:** dos anúncios em que o código marcou o campo, quantos estavam certos. Precisão baixa = o código inventa.
- **Cobertura:** dos anúncios que de fato têm o campo, quantos o código achou. Cobertura baixa = o código deixa passar.
- **F1:** uma nota só, que combina as duas.

**Por que por período?** Se a cobertura de um campo cai com o tempo (por exemplo, o OCR dos jornais mais antigos é pior), uma "queda" desse
campo nos anúncios pode ser só **efeito de leitura**, e não uma mudança na sociedade. Medir a cobertura em cada período mostra onde isso pode acontecer.

> **Cuidado ao ler:** os rótulos foram feitos por **Claude**, não pelo grupo de pesquisa; devem ser conferidos por pessoas.
> A amostra é pequena (cerca de 20 fugas por período), então os **intervalos são largos** (intervalo de Wilson de 95%).
> Períodos com menos de 20 anúncios que de fato têm o campo aparecem com círculo aberto nos gráficos.
""")

md("## Preparação: ler os rótulos e rodar o código local")
code('''
import json
import sys
from pathlib import Path

RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Markdown, display
from hdb import validacao
from hdb.estatistica import wilson

pd.set_option("display.width", 200)
plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
PERIODOS = validacao.PERIODOS
def periodo_curto(p):
    return p if p.startswith("antes") else p.split(" ")[0]
MIN_N = 20
ARQ = RAIZ / "tests" / "fixtures" / "campos_gold.json"
gold = json.loads(ARQ.read_text(encoding="utf-8")) if ARQ.exists() else []
rotulados = [g for g in gold if g.get("rotulos")]
SEM_ROTULOS = not rotulados
if SEM_ROTULOS:
    print("arquivo sem rótulos: rotule tests/fixtures/campos_gold.json")
    R = {c: {} for c in validacao.CAMPOS}
else:
    print(f"{len(rotulados)} anúncios rotulados ({sum(g['tipo'] == 'fuga' for g in rotulados)} fugas, "
          f"{sum(g['tipo'] == 'aluguel' for g in rotulados)} aluguéis)")
    R = validacao.comparar(rotulados)
if len(rotulados) != __N_COM__:
    print(f"ATENÇÃO: os comentários deste caderno foram escritos para __N_COM__ anúncios rotulados e agora são {len(rotulados)}: "
          "confira os números dos textos antes de usar.")

CAMPOS = [("recompensa", "Recompensa (fugas)"), ("nacao", "Cita nação (fugas)"), ("marcas", "Marcas no corpo (fugas)"),
          ("idade", "Idade: achou alguma (fugas)"), ("sexo", "Sexo f/m (todos)")]
fmt = lambda t: "–" if t[0] != t[0] else f"{100 * t[0]:.0f}% [{100 * t[1]:.0f}–{100 * t[2]:.0f}]"
''')

md("""
## 1. Precisão e cobertura de cada campo
`VP` = o código marcou e estava certo; `FP` = marcou e não devia; `FN` = deixou passar. Entre colchetes, o intervalo de 95%.
Em **idade** a cobertura é "o anúncio traz idade e o código achou alguma"; em **sexo**, "o anúncio diz f ou m e o código disse f ou m"
(um `FP` ali é o código dizer f/m onde o rótulo é "ambos" ou "não diz"). As linhas de **acerto** abaixo olham só os casos em que
rótulo e código acharam algo: a idade tem de cair a ±1 ano da rotulada (ou do intervalo rotulado), e o sexo tem de ser o mesmo.
""")
code('''
if SEM_ROTULOS:
    display(Markdown("_Arquivo sem rótulos: rotule `tests/fixtures/campos_gold.json`._"))
else:
    linhas = []
    for campo, nome in CAMPOS:
        c = R[campo].get(validacao.TOTAL)
        if c is None:
            continue
        m = validacao.metricas(c)
        linhas.append({"Campo": nome, "n": m["n"], "VP": c["vp"], "FP": c["fp"], "FN": c["fn"],
                       "Precisão [IC 95%]": fmt(m["precisao"]), "Cobertura [IC 95%]": fmt(m["cobertura"]), "F1 [IC 95%]": fmt(m["f1"])})
    display(pd.DataFrame(linhas).set_index("Campo"))
    acerto = []
    for campo, nome in (("idade_acerto", "Idade a ±1 ano, entre os que ambos acharam"), ("sexo_acerto", "Sexo certo, entre os que ambos acharam")):
        c = R[campo].get(validacao.TOTAL)
        if c:
            acerto.append({"Medida": nome, "n": c["vp"] + c["fp"], "Acertos": c["vp"],
                           "Taxa de acerto [IC 95%]": fmt(wilson(c["vp"], c["vp"] + c["fp"]))})
    display(pd.DataFrame(acerto).set_index("Medida"))
''')
com("c1")

md("""
## 2. Cobertura por período
Para cada campo, a cobertura (`VP / (VP + FN)`) em cada período, com intervalo de Wilson de 95%. **Círculo aberto** = menos de 20
anúncios que de fato têm o campo naquele período: o número é frágil.

O **teste de queda** compara a cobertura do primeiro período com pelo menos 20 positivos rotulados e a do último
(teste exato de Fisher). Sinalizamos quando a cobertura cai **mais de 15 pontos** e **p < 0,05**; sem isso, não dá para dizer que a leitura piorou.
""")
code('''
if SEM_ROTULOS:
    display(Markdown("_Arquivo sem rótulos: rotule `tests/fixtures/campos_gold.json`._"))
else:
    linhas = []
    for campo, nome in CAMPOS:
        lin = {"Campo": nome}
        for p in PERIODOS:
            c = R[campo].get(p)
            if c is None:
                lin[p] = "–"
                continue
            pos = c["vp"] + c["fn"]
            lin[p] = f"{fmt(wilson(c['vp'], pos))} (n+={pos}{' ⚠' if pos < MIN_N else ''})"
        linhas.append(lin)
    display(pd.DataFrame(linhas).set_index("Campo"))
    print("n+ = anúncios que de fato têm o campo; ⚠ = menos de 20.")

    fig, eixos = plt.subplots(1, len(CAMPOS), figsize=(3.0 * len(CAMPOS), 3.4), sharey=True)
    for ax, (campo, nome) in zip(eixos, CAMPOS):
        for i, p in enumerate(PERIODOS):
            c = R[campo].get(p)
            pos = (c["vp"] + c["fn"]) if c else 0
            if pos == 0:
                continue
            v, lo, hi = wilson(c["vp"], pos)
            ax.errorbar(i, v, yerr=[[v - lo], [hi - v]], color="#0072B2", capsize=3, lw=1.2)
            ax.plot(i, v, "o", color="#0072B2", mfc="white" if pos < MIN_N else "#0072B2", ms=7, zorder=3)
        ax.set_xticks(range(len(PERIODOS)))
        ax.set_xticklabels([periodo_curto(p).replace("antes de ", "<") for p in PERIODOS], rotation=30, ha="right")
        ax.set_title(nome, fontsize=9)
        ax.set_ylim(0, 1.02)
    eixos[0].set_ylabel("cobertura")
    fig.suptitle("Cobertura por período (círculo aberto: menos de 20 positivos)", fontsize=10)
    fig.tight_layout()
    plt.show()

    linhas = []
    for campo, nome in CAMPOS:
        q = validacao.queda_de_cobertura({p: R[campo][p] for p in PERIODOS if p in R[campo]}, min_n=MIN_N)
        if q == "sem n":
            linhas.append({"Campo": nome, "Resultado": "sem n (menos de 2 períodos com 20 positivos)"})
        else:
            ca, cu, queda, p, sinal = q
            linhas.append({"Campo": nome, "Cobertura do 1º": f"{100 * ca:.0f}%", "Cobertura do último": f"{100 * cu:.0f}%",
                           "Diferença (pontos)": round(queda, 1), "p (Fisher)": round(p, 3),
                           "Resultado": "QUEDA SINALIZADA" if sinal else "sem queda sinalizada"})
    display(pd.DataFrame(linhas).set_index("Campo").fillna(""))
''')
com("c2")

md("""
## 2b. A verdade por período contra o que o código vê
Nas **fugas rotuladas** (20 por período), quantas de fato têm o campo (**verdade**) e quantas o código achou (**código**), e o teste exato de Fisher entre o
primeiro e o último período. Se o código vê uma queda **maior** que a real, parte da queda é **efeito de leitura** (o OCR ou a grafia escondem o campo).
Com 20 anúncios por período o teste tem pouco poder: **p alto não prova que não houve mudança**, só que esta amostra não a mostra.
""")
code('''
if SEM_ROTULOS:
    display(Markdown("_Arquivo sem rótulos._"))
else:
    from scipy.stats import fisher_exact
    fugas = [g for g in rotulados if g["tipo"] == "fuga"]
    ext = {g["id"]: validacao.extrair_para_comparar(g["texto"]) for g in fugas}
    def tem(g, campo, fonte):
        if fonte == "verdade":
            r = g["rotulos"]
            return bool(r["nacoes"]) if campo == "nacao" else (r["idade"] is not None if campo == "idade" else bool(r[campo]))
        e = ext[g["id"]]
        return bool(e["nacoes"]) if campo == "nacao" else (e["idade"] is not None if campo == "idade" else bool(e[campo]))
    linhas = []
    for campo, nome in (("recompensa", "Recompensa"), ("nacao", "Nação citada"), ("marcas", "Marcas no corpo"), ("idade", "Idade citada")):
        for fonte in ("verdade", "código"):
            ks = []
            for per in PERIODOS:
                gp = [g for g in fugas if periodo_curto(g["periodo"]) == per]
                ks.append((sum(tem(g, campo, fonte) for g in gp), len(gp)))
            (k1, n1), (k2, n2) = ks[0], ks[-1]
            p = fisher_exact([[k1, n1 - k1], [k2, n2 - k2]])[1]
            linhas.append({"Campo": nome, "Fonte": fonte,
                           **{per: f"{k}/{n} ({100 * k / n:.0f}%)" for per, (k, n) in zip(PERIODOS, ks)},
                           "p (1º × último)": "<0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")})
    display(pd.DataFrame(linhas).set_index(["Campo", "Fonte"]))
''')
com("c2b")

md("""
## 3. Onde o código erra
Até 10 **falsos negativos** (o campo existe e o código não achou) e 10 **falsos positivos** (o código marcou e não devia) por campo,
com o começo do texto, o rótulo e o que o código extraiu.
""")
code('''
if SEM_ROTULOS:
    display(Markdown("_Arquivo sem rótulos: rotule `tests/fixtures/campos_gold.json`._"))
else:
    for campo, nome in CAMPOS:
        c = R[campo].get(validacao.TOTAL)
        if c is None:
            continue
        fn = [e for e in c["erros"] if e["rotulo"] and not e["extraido"]]
        fp = [e for e in c["erros"] if e["extraido"] and not e["rotulo"]]
        outros = [e for e in c["erros"] if e not in fn and e not in fp]   # sexo: rótulo f/m e código disse o contrário etc.
        display(Markdown(f"### {nome}: {c['fn']} falsos negativos, {c['fp']} falsos positivos"))
        for titulo, lista in (("Falsos negativos", fn), ("Falsos positivos", fp), ("Outros erros", outros)):
            if not lista:
                continue
            tabela = pd.DataFrame([{"id": e["id"], "rótulo": e["rotulo"], "código": e["extraido"], "trecho": e["trecho"]}
                                   for e in lista[:10]]).set_index("id")
            display(Markdown(f"**{titulo}** (mostrando {min(10, len(lista))} de {len(lista)})"))
            with pd.option_context("display.max_colwidth", 200):
                display(tabela)
''')

md("""
## 4. O que isso diz e o que não diz
""")
md(COM.get("c3", "_(a preencher)_"))

for _c in cells:  # nº de itens rotulados para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
