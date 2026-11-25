import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "incerteza.ipynb"
JC = Path(__file__).with_name("comentarios_incerteza.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Margem de erro e tendência: o que os números sustentam

Este caderno responde: **as mudanças que vemos de um período legal para outro são reais ou podem ser sorte da amostra?**
Cada porcentagem ou média dos outros cadernos é uma estimativa feita com poucos ou muitos anúncios. Aqui damos a cada uma
uma **margem de erro** e testamos se há uma **tendência** ao longo dos quatro períodos, para 9 medidas fixas (a lista não muda
conforme o resultado, para não escolhermos só o que deu certo).

Corpus `{config.VERSAO_CORPUS}`, campos `{config.VERSAO_CAMPOS}`, temas `{config.VERSAO_TOPICOS}`. Os números dos comentários foram lidos da saída
da própria execução; se o banco mudar, **confira os números de novo**.

- **Intervalo de Wilson (proporções):** a faixa de valores plausíveis para a porcentagem verdadeira, dado quantos anúncios há no grupo; grupos pequenos têm faixas largas.
- **Bootstrap (médias e medianas):** sorteamos os anúncios do grupo, com reposição, 2000 vezes; a faixa é onde caem 95% dos resultados.
- **Tendência:** teste de Cochran–Armitage (proporções) ou correlação de Spearman (valores contínuos) entre a ordem do período e a medida; o p diz quão raro seria ver essa tendência só por acaso.
- **p ajustado (Benjamini–Hochberg):** como fazemos 9 testes, alguns passariam por sorte; o ajuste corrige isso.

> **Cuidado ao ler:** (1) os anúncios foram achados por **frases de busca**, não por sorteio: a margem de erro mede só o
> erro de amostragem *dentro do que a busca achou*, não o viés da busca. (2) **O bootstrap usa o modelo de temas fixo:** mede o erro de
> amostragem dos anúncios, **não a instabilidade do LDA** (outra semente poderia reorganizar os temas). (3) Células com
> **n < 30 vêm marcadas com ⚠**: a faixa é larga e frágil. (4) Os anúncios de um mesmo período não são independentes (reanúncios, mesmo dono), o que torna as faixas um pouco otimistas.
""")

md("## Preparação: ler o corpus, os campos e os temas")
code('''
import sys
from pathlib import Path

RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
from hdb import config
from hdb.banco import BancoSupabase
from hdb.categorias import categorias
from hdb.estatistica import bootstrap_ic, cochran_armitage, diferenca_ic, fdr_bh, spearman_tendencia, wilson
from hdb.topicos import nomear

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
banco = BancoSupabase()
db = banco.cliente      # lê o config/.env pelo módulo hdb

def ler_tudo(consulta, bloco=1000):
    """Executa a consulta em blocos de 1000 linhas e junta o resultado."""
    linhas, inicio = [], 0
    while True:
        parte = consulta().range(inicio, inicio + bloco - 1).execute().data
        linhas += parte
        if len(parte) < bloco:
            return pd.DataFrame(linhas)
        inicio += bloco

PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
def periodo_curto(p):
    return p if p.startswith("antes") else p.split(" ")[0]
MIN_N = 30
MODELO = config.VERSAO_TOPICOS

corpus = pd.DataFrame(banco.anuncios_do_corpus(config.VERSAO_CORPUS))
corpus = corpus[corpus["texto_padrao"].fillna("").str.strip() != ""][["id", "periodo_legal"]]
# campos e texto ORIGINAL (para as marcas no corpo), da view anuncios_completos
extra = ler_tudo(lambda: db.table("anuncios_completos")
                 .select("id,texto,c_tipo,c_sexo,c_idade_min,c_idade_max,c_nacoes,c_recompensa")
                 .in_("versao", list(config.VERSOES_ANUNCIOS)).eq("c_versao", config.VERSAO_CAMPOS).order("id")).drop_duplicates("id")
df = corpus.merge(extra, on="id", how="left")
df["periodo"] = df["periodo_legal"].map(lambda p: periodo_curto(p) if isinstance(p, str) else None)
df = df[df["periodo"].isin(PERIODOS)].copy()
df["idade"] = df[["c_idade_min", "c_idade_max"]].astype(float).mean(axis=1)
tem = lambda s: s.map(lambda v: isinstance(v, list) and len(v) > 0)
print(f"{len(df)} anúncios no corpus {config.VERSAO_CORPUS} com período legal")
if len(df) != __N_COM__:
    print(f"ATENÇÃO: os comentários deste caderno foram escritos para __N_COM__ anúncios e agora são {len(df)}: "
          "confira os números dos textos antes de usar.")

# misturas de temas do modelo da rodada, com os nomes sugeridos (topicos.nomear sobre as 12 palavras de maior peso)
palavras = ler_tudo(lambda: db.table("topico_palavras").select("topico,palavra,peso").eq("versao", MODELO)
                    .order("topico").order("peso", desc=True))
dist = ler_tudo(lambda: db.table("anuncio_topicos").select("anuncio_id,topico,proporcao").eq("versao", MODELO)
                .order("anuncio_id").order("topico"))
NOMES = nomear({t: g.sort_values("peso", ascending=False)["palavra"].head(12) for t, g in palavras.groupby("topico")})
pivo = dist.pivot(index="anuncio_id", columns="topico", values="proporcao").rename(columns=NOMES)
temas = df.set_index("id")[["periodo"]].join(pivo, how="inner")
print(f"{len(temas)} anúncios com mistura de temas no modelo {MODELO}")
print("Temas:", "; ".join(f"T{t} {n}" for t, n in NOMES.items()))

def soma_temas(predicado):
    cols = [n for n in pivo.columns if predicado(n)]
    return temas[cols].sum(axis=1) if cols else None   # None = tema ausente neste modelo

plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
COR = "#0072B2"
''')

md("""
## 1. As 9 medidas
Cada medida tem seu grupo (quem entra no denominador) e seu tipo: **proporção** (Wilson; tendência de Cochran–Armitage)
ou **contínua** (bootstrap; tendência de Spearman sobre a ordem do período, anúncio a anúncio).
1. % de anúncios que são **fuga** (todo o corpus). 2. % de fugas **com recompensa**. 3. % de fugas **com nação**.
4. % de fugas **com marcas no corpo** (texto original). 5. **idade mediana** dos fugidos. 6. **% feminino nos aluguéis**
(entre os que dizem o sexo). 7. **parcela dos temas de fuga** somados. 8. **parcela dos temas de serviço doméstico** somados.
9. **parcela do tema "Ama de leite"**.
""")
code('''
fuga = df[df["c_tipo"] == "fuga"]
alug = df[(df["c_tipo"] == "aluguel") & df["c_sexo"].isin(["f", "m"])]
marcas = fuga["texto"].map(lambda t: len(categorias(t)["marcas"]) > 0 if isinstance(t, str) else False)

def _g(base, serie):  # DataFrame (periodo, v) ou None
    return pd.DataFrame({"periodo": base["periodo"], "v": serie.astype(float)}).dropna()

def _tema(serie):
    return None if serie is None else pd.DataFrame({"periodo": temas["periodo"], "v": serie.astype(float)})

# (nome, tipo, unidade, dados)
MEDIDAS = [
    ("1. % de anúncios que são fuga", "prop", "%", _g(df, df["c_tipo"] == "fuga")),
    ("2. % de fugas com recompensa", "prop", "%", _g(fuga, fuga["c_recompensa"].fillna(False).astype(bool))),
    ("3. % de fugas com nação", "prop", "%", _g(fuga, tem(fuga["c_nacoes"]))),
    ("4. % de fugas com marcas no corpo", "prop", "%", _g(fuga, marcas)),
    ("5. Idade mediana dos fugidos (anos)", "mediana", "anos", _g(fuga, fuga["idade"])),
    ("6. % feminino nos aluguéis", "prop", "%", _g(alug, alug["c_sexo"] == "f")),
    ("7. Parcela dos temas de fuga (%)", "media", "%", _tema(soma_temas(lambda n: n.startswith("Fuga")))),
    ("8. Parcela dos temas de serviço doméstico (%)", "media", "%",
     _tema(soma_temas(lambda n: n.startswith("Mulheres: lavar") or n.startswith("Aluguel de pretos e moleques")))),
    ("9. Parcela do tema Ama de leite (%)", "media", "%", _tema(soma_temas(lambda n: n == "Ama de leite"))),
]
print(f"{len(MEDIDAS)} medidas; ausentes no modelo {MODELO}: {[m[0] for m in MEDIDAS if m[3] is None] or 'nenhuma'}")
''')

md("""
## 2. Cálculo: valor e margem de erro por período, tendência e diferença
Valor e IC de 95% por período; p de tendência; p ajustado (Benjamini–Hochberg sobre as 9 medidas); e a diferença do
último período com dados menos o primeiro, com IC por bootstrap.
""")
code('''
FATOR = lambda tipo: 100 if tipo != "mediana" else 1   # proporções e parcelas em %, idade em anos
RES = {}
for nome, tipo, unidade, d in MEDIDAS:
    if d is None or d.empty:
        RES[nome] = None
        continue
    f = FATOR(tipo)
    por = {}
    for p in PERIODOS:
        v = d.loc[d["periodo"] == p, "v"].to_numpy()
        n = len(v)
        if tipo == "prop":
            est, lo, hi = wilson(int(v.sum()), n)
        elif n == 0:
            est = lo = hi = float("nan")
        else:
            est, lo, hi = bootstrap_ic(v, np.median if tipo == "mediana" else np.mean)
        por[p] = {"n": n, "valor": est * f, "baixo": lo * f, "alto": hi * f, "v": v}
    com_dados = [p for p in PERIODOS if por[p]["n"] > 0]
    if tipo == "prop":
        z, pval = cochran_armitage([int(por[p]["v"].sum()) for p in com_dados], [por[p]["n"] for p in com_dados])
        estat = np.mean
    else:
        ordem = d["periodo"].map(PERIODOS.index).to_numpy()
        _, pval = spearman_tendencia(ordem, d["v"].to_numpy())
        estat = np.median if tipo == "mediana" else np.mean
    prim, ult = (com_dados[0], com_dados[-1]) if len(com_dados) >= 2 else (None, None)
    if prim:
        dif, dlo, dhi = diferenca_ic(por[prim]["v"], por[ult]["v"], estat)
    else:
        dif = dlo = dhi = float("nan")
    RES[nome] = {"tipo": tipo, "unidade": unidade, "por": por, "p": pval, "prim": prim, "ult": ult,
                 "dif": dif * f, "dlo": dlo * f, "dhi": dhi * f}
nomes_ok = [m[0] for m in MEDIDAS]
padj = fdr_bh([RES[n]["p"] if RES[n] else float("nan") for n in nomes_ok])
for n, pa in zip(nomes_ok, padj):
    if RES[n]:
        RES[n]["padj"] = float(pa)

def veredito(r):
    if r is None:
        return "tema ausente"
    if r["prim"] is None or np.isnan(r["p"]):
        return "sem dados suficientes"
    if r["por"][r["prim"]]["n"] < MIN_N or r["por"][r["ult"]]["n"] < MIN_N:
        return "frágil (n<30)"
    if r["padj"] < 0.05 and not (r["dlo"] <= 0 <= r["dhi"]):
        return "sustenta"
    return "não sustenta"

nf = lambda x, c=1: "—" if x is None or np.isnan(x) else f"{x:.{c}f}".replace(".", ",")
def pf(x):
    return "—" if x is None or np.isnan(x) else ("<0,001" if x < 0.001 else f"{x:.3f}".replace(".", ","))
def cel(c):
    return f"{nf(c['valor'])} [{nf(c['baixo'])}; {nf(c['alto'])}]" + (" ⚠" if c["n"] < MIN_N else "")

linhas = []
for n in nomes_ok:
    r = RES[n]
    if r is None:
        linhas.append({"Medida": n, "1º período": "tema ausente", "Último período": "—", "Diferença [IC 95%]": "—",
                       "p": "—", "p ajustado": "—", "Tendência": "tema ausente"})
        continue
    a, b = r["por"].get(r["prim"]) if r["prim"] else None, r["por"].get(r["ult"]) if r["ult"] else None
    linhas.append({"Medida": n,
                   "1º período": f"{r['prim']}: {nf(a['valor'])} (n={a['n']}{' ⚠' if a['n'] < MIN_N else ''})" if a else "—",
                   "Último período": f"{r['ult']}: {nf(b['valor'])} (n={b['n']}{' ⚠' if b['n'] < MIN_N else ''})" if b else "—",
                   "Diferença [IC 95%]": f"{nf(r['dif'])} [{nf(r['dlo'])}; {nf(r['dhi'])}]",
                   "p": pf(r["p"]), "p ajustado": pf(r.get("padj")), "Tendência": veredito(r)})
RESUMO = pd.DataFrame(linhas).set_index("Medida")
print("Valores em % (idade em anos); diferença = último período com dados − primeiro; ⚠ = n < 30.")
RESUMO
''')
com("c1")

md("""
## 3. Tabela detalhada por período
Valor e intervalo de 95% de cada medida em cada período, com o `n` do grupo. `⚠` = menos de 30 anúncios no grupo.
""")
code('''
det = []
for n in nomes_ok:
    r = RES[n]
    for p in PERIODOS:
        if r is None:
            det.append({"Medida": n, "Período": p, "n": "—", "Valor [IC 95%]": "tema ausente"})
        else:
            c = r["por"][p]
            det.append({"Medida": n, "Período": p, "n": f"{c['n']} ⚠" if c["n"] < MIN_N else str(c["n"]),
                        "Valor [IC 95%]": "sem anúncios" if c["n"] == 0 else cel(c)})
pd.DataFrame(det).set_index(["Medida", "Período"])
''')

md("""
## 4. Gráficos: valor e margem de erro por período
Um painel por medida; a barra é o IC de 95%. Pontos **vazados** (círculo aberto) têm n < 30.
""")
code('''
fig, eixos = plt.subplots(3, 3, figsize=(12, 9))
for ax, n in zip(eixos.ravel(), nomes_ok):
    r = RES[n]
    ax.set_title(n, fontsize=9, loc="left")
    if r is None:
        ax.text(0.5, 0.5, "tema ausente", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        continue
    for i, p in enumerate(PERIODOS):
        c = r["por"][p]
        if c["n"] == 0:
            continue
        ax.errorbar(i, c["valor"], yerr=[[max(c["valor"] - c["baixo"], 0)], [max(c["alto"] - c["valor"], 0)]], fmt="o", color=COR,
                    ecolor=COR, capsize=3, mfc="white" if c["n"] < MIN_N else COR)
    ax.set_xticks(range(len(PERIODOS)))
    ax.set_xticklabels([p.replace("antes de ", "<") for p in PERIODOS], fontsize=8)
    ax.set_ylabel(r["unidade"]); ax.set_xlim(-0.4, len(PERIODOS) - 0.6)
    ax.set_xlabel(f"{veredito(r)} (p aj. = {pf(r.get('padj'))})", fontsize=8)
fig.suptitle("Valor e IC de 95% por período legal (círculo aberto = n < 30)")
fig.tight_layout(); plt.show()
''')
com("c2")

md("""
## 5. O que sustenta e o que não sustenta
**Sustenta** = p ajustado < 0,05 **e** o IC da diferença (último − primeiro) não contém zero; **frágil** = o primeiro ou o último
período tem n < 30; **não sustenta** = o restante. "Não sustenta" não prova que não houve mudança: pode ser só que faltem anúncios.
""")
md(COM.get("c3", "_(a preencher)_"))

md("""
## 6. Consenso entre sementes
O bootstrap acima usa o modelo de temas **fixo**. Aqui medimos a outra fonte de incerteza: **o LDA depende da semente**.
Treinamos o mesmo modelo (mesmo corpus, 6 temas, mesmos parâmetros) com 30 sementes fixas, emparelhamos cada rodada com a
rodada de referência (método húngaro sobre a distância de Jensen–Shannon entre as distribuições de palavras) e olhamos:
(a) em quantas sementes cada tema da referência reaparece (**estabilidade**; abaixo de 70% = **instável**) e (b) o intervalo
(2,5–97,5% entre sementes) da **parcela do tema por período**. O limiar de "mesmo tema" é metade da mediana das distâncias
entre temas distintos da referência. Nada é gravado no banco: o resumo vem de `data/consenso_topicos.json`.
""")
code('''
import json
arq = RAIZ / "data" / "consenso_topicos.json"
if not arq.exists():
    display(Markdown("**Aviso:** `data/consenso_topicos.json` não existe. Rode `python scripts/consenso_topicos.py` e gere o caderno de novo."))
else:
    C = json.loads(arq.read_text(encoding="utf-8"))
    print(f"{C['n_anuncios']} anúncios, {C['n_sementes']} sementes, semente de referência {C['semente_ref']}; "
          f"limiar JS = {C['limiar']:.3f}; instável se estabilidade < {C['min_estavel']:.0%}")
    est = pd.DataFrame([{"Tema (referência)": t["nome"], "Palavras": ", ".join(t["palavras"][:6]),
                         "Estabilidade": f"{t['estabilidade']:.0%}", "Distância mediana": round(t["dist_mediana"], 3),
                         "Situação": "instável" if t["instavel"] else "estável"} for t in C["temas"]]).set_index("Tema (referência)")
    display(est)
    ps = C["periodos"]
    lin = [{"Tema": t["nome"], **{p: f"{t['parcela'][p]['mediana']:.1%} [{t['parcela'][p]['p2_5']:.1%}; {t['parcela'][p]['p97_5']:.1%}]" for p in ps}}
           for t in C["temas"]]
    display(Markdown("Parcela do tema por período: **mediana [2,5%; 97,5%]** entre as sementes (tema emparelhado à referência)."))
    display(pd.DataFrame(lin).set_index("Tema"))
''')
com("c_consenso")

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
