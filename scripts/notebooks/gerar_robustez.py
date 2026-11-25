import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "robustez_mistura.ipynb"
JC = Path(__file__).with_name("comentarios_robustez.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Robustez: as tendências sobrevivem à mistura de tipos e ao jornal?

O caderno `incerteza` mostrou que várias mudanças entre os períodos legais **não são sorte da amostra**. Aqui fazemos outra pergunta:
**elas não seriam um efeito de composição?** Duas confusões possíveis:

1. **Mistura de tipos.** Se num período há mais anúncios de fuga e noutro mais de aluguel, parcelas de temas (fuga, serviço doméstico,
   ama de leite) mudam só porque a mistura mudou, não porque os anúncios de cada tipo mudaram.
2. **Fonte.** Parte dos anúncios vem de outros jornais (bibs `094170_01` e `706744`); se eles pesam diferente em cada período, a tendência
   pode ser de jornal, não de época.

Refazemos as **mesmas 9 medidas** do caderno `incerteza` em **quatro visões**:

| Visão | O que é |
|---|---|
| **Bruta** | como no caderno `incerteza` |
| **Ajustada** | a mistura de tipos é igualada entre os períodos (padronização, abaixo) |
| **Só JC** | só o Jornal do Commercio (sem os bibs `094170_01` e `706744`) |
| **Ajustada + JC** | as duas coisas |

**Como se ajusta a mistura.** Cada anúncio recebe um peso = (fatia do seu tipo no corpus todo) ÷ (fatia do seu tipo no seu período), entre os
4 tipos **fuga, aluguel, venda e ama de leite**. Assim, depois de pesar, todos os períodos têm a mesma mistura de tipos e a diferença que sobra
não vem dela. **Anúncios de compra ficam de fora das visões ajustadas** (peso 0). O ajuste vale para as medidas **7, 8 e 9** (parcelas de temas);
as medidas **2 a 6** já são calculadas dentro de um tipo (fuga ou aluguel), então ajustada = bruta e só mudam em "só JC" (mostramos "—" nas colunas
ajustadas). A medida **1** (% de anúncios que são fuga) **é** a própria mistura: não se ajusta, só tem a visão "só JC", e mede o que a **busca achou**.

**n efetivo.** Com pesos, anúncios valem quantidades diferentes e a amostra "vale" menos que o n bruto: `n efetivo = (Σ pesos)² / Σ pesos²`
(com pesos iguais é o próprio n). **⚠ marca n ou n efetivo < 30**: a faixa é larga e frágil. Em "só JC", o período **antes de 1831** fica com poucos
anúncios e quase sempre vem marcado ⚠.

**Bootstrap ponderado.** Sorteamos anúncios com reposição levando o peso junto e recalculamos a média ponderada de cada período (2.000 repetições);
a diferença é último − primeiro período, com o mesmo bootstrap. Para as parcelas ajustadas, a tendência é um **teste de permutação**: dentro de cada tipo
embaralhamos o período entre os anúncios (1.000 vezes) e comparamos a inclinação (mínimos quadrados ponderados da parcela contra o escore do período, 1 a 4).
Nas visões não ajustadas ficam os testes do caderno `incerteza` (Cochran–Armitage nas proporções, Spearman nas contínuas). O p ajustado (Benjamini–Hochberg)
é calculado dentro de cada visão, sobre as medidas que se aplicam a ela.

**"Mantém?"** compara a visão bruta com as outras visões aplicáveis à medida: **mantém** = mesmo sinal e IC da diferença sem zero em todas;
**parcial** = em algumas; **não mantém** = em nenhuma; **frágil** = alguma visão necessária tem n ou n efetivo < 30 no primeiro ou no último período.

Corpus `{config.VERSAO_CORPUS}`, campos `{config.VERSAO_CAMPOS}`, temas `{config.VERSAO_TOPICOS}`. Os números dos comentários foram lidos da saída
da própria execução; se o banco mudar, **confira os números de novo**.

> **Cuidado ao ler:** (1) os anúncios vêm de **frases de busca**, não de sorteio; (2) **o bootstrap usa o modelo de temas fixo e não mede a
> instabilidade do LDA** (outra semente poderia reorganizar os temas); (3) os anúncios de um período não são independentes (reanúncios, mesmo dono),
> então as faixas são um pouco otimistas; (4) ajustar a mistura **não elimina** outros vieses (o que a busca achou, mudanças de formato do jornal).
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
from hdb.ajustes import (diferenca_ponderada_ic, inclinacao_permutacao, media_ponderada_ic, n_efetivo,
                         pesos_mistura, so_jc)
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
                 .select("id,texto,bib,c_tipo,c_sexo,c_idade_min,c_idade_max,c_nacoes,c_recompensa")
                 .in_("versao", list(config.VERSOES_ANUNCIOS)).eq("c_versao", config.VERSAO_CAMPOS).order("id")).drop_duplicates("id")
df = corpus.merge(extra, on="id", how="left")
df["periodo"] = df["periodo_legal"].map(lambda p: periodo_curto(p) if isinstance(p, str) else None)
df = df[df["periodo"].isin(PERIODOS)].copy()
df["idade"] = df[["c_idade_min", "c_idade_max"]].astype(float).mean(axis=1)
tem = lambda s: s.map(lambda v: isinstance(v, list) and len(v) > 0)
# pesos da padronização: sobre o corpus todo e sobre o corpus só do Jornal do Commercio
df["w_aj"] = pesos_mistura(df)
jc_ = so_jc(df)
df["w_ajjc"] = pesos_mistura(jc_).reindex(df.index).fillna(0.0)
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
temas = df.set_index("id")[["periodo", "bib", "c_tipo", "w_aj", "w_ajjc"]].join(pivo, how="inner")
print(f"{len(temas)} anúncios com mistura de temas no modelo {MODELO}")
print("Temas:", "; ".join(f"T{t} {n}" for t, n in NOMES.items()))

def soma_temas(predicado):
    cols = [n for n in pivo.columns if predicado(n)]
    return temas[cols].sum(axis=1) if cols else None   # None = tema ausente neste modelo

plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
COR = "#0072B2"
''')


md("""
## 1. Tabela resumo: as 9 medidas em quatro visões
Cada célula: valor no **1º → último** período (ver coluna do período no rodapé), diferença último − primeiro com IC de 95%, e o p ajustado da visão.
"—" = a visão não se aplica à medida. ⚠ = n ou n efetivo < 30 no primeiro ou no último período dessa visão. **Mantém?** compara a bruta com as outras visões;
**Sem as frágeis** repete o veredito ignorando as visões marcadas ⚠ (para mostrar o que as visões bem medidas dizem).
""")
code('''
VISOES = ["Bruta", "Ajustada", "Só JC", "Ajustada + JC"]
SIGLA = {"Bruta": "bruta", "Ajustada": "aj", "Só JC": "jc", "Ajustada + JC": "ajjc"}
FATOR = lambda tipo: 100 if tipo != "mediana" else 1   # proporções e parcelas em %, idade em anos

def _base(d, serie):
    b = d[["periodo", "bib", "c_tipo", "w_aj", "w_ajjc"]].copy()
    b["v"] = serie.astype(float)
    return b.dropna(subset=["v"])

def _tema(serie):
    if serie is None:
        return None
    b = temas[["periodo", "bib", "c_tipo", "w_aj", "w_ajjc"]].copy()
    b["v"] = serie.astype(float)
    return b

fuga = df[df["c_tipo"] == "fuga"]
alug = df[(df["c_tipo"] == "aluguel") & df["c_sexo"].isin(["f", "m"])]
marcas = fuga["texto"].map(lambda t: len(categorias(t)["marcas"]) > 0 if isinstance(t, str) else False)
SEM_AJ = ("Bruta", "Só JC")
TODAS = tuple(VISOES)

# (nome, tipo, unidade, base, visões aplicáveis)
MEDIDAS = [
    ("1. % de anúncios que são fuga", "prop", "%", _base(df, df["c_tipo"] == "fuga"), SEM_AJ),
    ("2. % de fugas com recompensa", "prop", "%", _base(fuga, fuga["c_recompensa"].fillna(False).astype(bool)), SEM_AJ),
    ("3. % de fugas com nação", "prop", "%", _base(fuga, tem(fuga["c_nacoes"])), SEM_AJ),
    ("4. % de fugas com marcas no corpo", "prop", "%", _base(fuga, marcas), SEM_AJ),
    ("5. Idade mediana dos fugidos (anos)", "mediana", "anos", _base(fuga, fuga["idade"]), SEM_AJ),
    ("6. % feminino nos aluguéis", "prop", "%", _base(alug, alug["c_sexo"] == "f"), SEM_AJ),
    ("7. Parcela dos temas de fuga (%)", "media", "%", _tema(soma_temas(lambda n: n.startswith("Fuga"))), TODAS),
    ("8. Parcela dos temas de serviço doméstico (%)", "media", "%",
     _tema(soma_temas(lambda n: n.startswith("Mulheres: lavar") or n.startswith("Aluguel de pretos e moleques"))), TODAS),
    ("9. Parcela do tema Ama de leite (%)", "media", "%", _tema(soma_temas(lambda n: n == "Ama de leite")), TODAS),
]
nomes_ok = [m[0] for m in MEDIDAS]

def dados_da_visao(base, visao):
    """DataFrame (periodo, v, w, c_tipo) da visão: pesos 1 nas visões sem ajuste; peso 0 sai nas ajustadas."""
    if visao == "Bruta":
        d = base.assign(w=1.0)
    elif visao == "Só JC":
        d = so_jc(base).assign(w=1.0)
    elif visao == "Ajustada":
        d = base.assign(w=base["w_aj"])
    else:
        d = so_jc(base).assign(w=lambda x: x["w_ajjc"])
    return d[d["w"] > 0][["periodo", "v", "w", "c_tipo"]]

def calcular(d, tipo, visao, prim=None, ult=None):
    f = FATOR(tipo)
    ponderado = visao in ("Ajustada", "Ajustada + JC")
    por = {}
    if ponderado:
        est = media_ponderada_ic(d["v"], d["w"], d["periodo"], n=2000)
    for p in PERIODOS:
        x = d[d["periodo"] == p]
        v = x["v"].to_numpy()
        n = len(v)
        neff = n_efetivo(x["w"]) if ponderado else float(n)
        if n == 0:
            e = lo = hi = float("nan")
        elif ponderado:
            e, lo, hi = est[p]
        elif tipo == "prop":
            e, lo, hi = wilson(int(v.sum()), n)
        else:
            e, lo, hi = bootstrap_ic(v, np.median if tipo == "mediana" else np.mean)
        por[p] = {"n": n, "neff": neff, "valor": e * f, "baixo": lo * f, "alto": hi * f, "v": v, "w": x["w"].to_numpy()}
    com_dados = [p for p in PERIODOS if por[p]["n"] > 0]
    if prim is None:
        prim, ult = (com_dados[0], com_dados[-1]) if len(com_dados) >= 2 else (None, None)
    # tendência
    if ponderado:
        _, pval = inclinacao_permutacao(d["periodo"].map(PERIODOS.index) + 1, d["v"], d["w"], d["c_tipo"])
    elif tipo == "prop":
        _, pval = cochran_armitage([int(por[p]["v"].sum()) for p in com_dados], [por[p]["n"] for p in com_dados])
    else:
        _, pval = spearman_tendencia(d["periodo"].map(PERIODOS.index), d["v"])
    # diferença último − primeiro
    if prim is None or por[prim]["n"] == 0 or por[ult]["n"] == 0:
        dif = dlo = dhi = float("nan")
    elif ponderado:
        dif, dlo, dhi = diferenca_ponderada_ic(por[prim]["v"], por[prim]["w"], por[ult]["v"], por[ult]["w"])
    else:
        dif, dlo, dhi = diferenca_ic(por[prim]["v"], por[ult]["v"], np.median if tipo == "mediana" else np.mean)
    return {"por": por, "p": pval, "prim": prim, "ult": ult, "dif": dif * f, "dlo": dlo * f, "dhi": dhi * f}

RES = {}   # RES[medida][visão]
for nome, tipo, unidade, base, aplic in MEDIDAS:
    RES[nome] = {}
    if base is None or base.empty:
        continue
    r0 = calcular(dados_da_visao(base, "Bruta"), tipo, "Bruta")
    RES[nome]["Bruta"] = r0
    for vis in aplic:
        if vis != "Bruta":
            RES[nome][vis] = calcular(dados_da_visao(base, vis), tipo, vis, r0["prim"], r0["ult"])
# p ajustado por visão, sobre as medidas aplicáveis a ela
for vis in VISOES:
    ns = [n for n in nomes_ok if vis in RES[n]]
    for n, pa in zip(ns, fdr_bh([RES[n][vis]["p"] for n in ns])):
        RES[n][vis]["padj"] = float(pa)

def fragil(r):
    return r["prim"] is None or min(r["por"][r["prim"]]["neff"], r["por"][r["ult"]]["neff"]) < MIN_N

def segura(r, rb):
    """Mesmo sinal da bruta e IC da diferença sem zero."""
    return (not np.isnan(r["dif"])) and np.sign(r["dif"]) == np.sign(rb["dif"]) and not (r["dlo"] <= 0 <= r["dhi"])

def mantem(n, ignorar_frageis=False):
    rs = RES[n]
    if not rs:
        return "tema ausente"
    rb = rs["Bruta"]
    outras = [v for v in rs if v != "Bruta"]
    if ignorar_frageis:
        outras = [v for v in outras if not fragil(rs[v])]
        if fragil(rb) or not outras:
            return "—"
    elif fragil(rb) or any(fragil(rs[v]) for v in outras):
        return "frágil"
    if np.isnan(rb["dif"]) or rb["dlo"] <= 0 <= rb["dhi"]:
        return "sem efeito na bruta"
    ok = [segura(rs[v], rb) for v in outras]
    return "mantém" if all(ok) else "parcial" if any(ok) else "não mantém"

nf = lambda x, c=1: "—" if x is None or np.isnan(x) else f"{x:.{c}f}".replace(".", ",")
def pf(x):
    return "—" if x is None or np.isnan(x) else ("<0,001" if x < 0.001 else f"{x:.3f}".replace(".", ","))

def resumo_cel(r):
    if r is None:
        return "—"
    a, b = r["por"][r["prim"]], r["por"][r["ult"]]
    return (f"{nf(a['valor'])} → {nf(b['valor'])}; Δ {nf(r['dif'])} [{nf(r['dlo'])}; {nf(r['dhi'])}]; p aj. {pf(r.get('padj'))}"
            + (" ⚠" if fragil(r) else ""))

linhas = []
for n in nomes_ok:
    rs = RES[n]
    if not rs:
        linhas.append({"Medida": n, **{v: "tema ausente" for v in VISOES}, "n efetivo mín.": "—", "Mantém?": "tema ausente", "Sem as frágeis": "—"})
        continue
    neffs = [min(r["por"][r["prim"]]["neff"], r["por"][r["ult"]]["neff"]) for r in rs.values()]
    linhas.append({"Medida": n, **{v: resumo_cel(rs.get(v)) for v in VISOES},
                   "n efetivo mín.": f"{min(neffs):.0f}" + (" ⚠" if min(neffs) < MIN_N else ""),
                   "Mantém?": mantem(n), "Sem as frágeis": mantem(n, True)})
RESUMO = pd.DataFrame(linhas).set_index("Medida")
r1 = next(iter(r for r in RES[nomes_ok[0]].values()))
print(f"Períodos comparados: 1º = {r1['prim']}, último = {r1['ult']} (os mesmos nas quatro visões). Valores em % (idade em anos).")
pd.set_option("display.max_colwidth", 80)
RESUMO
''')
com("c1")

md("""
## 2. Parcelas dos temas por período nas quatro visões (medidas 7 a 9)
Valor e IC de 95% por período, com o n (e o **n efetivo** entre colchetes nas visões ajustadas). ⚠ = n ou n efetivo < 30.
""")
code('''
det = []
for n in nomes_ok[6:]:
    for p in PERIODOS:
        linha = {"Medida": n, "Período": p}
        for v in VISOES:
            r = RES[n].get(v)
            if r is None:
                linha[v] = "—"
                continue
            c = r["por"][p]
            ponderado = v in ("Ajustada", "Ajustada + JC")
            ne = f"n={c['n']}" + (f" [ef. {c['neff']:.0f}]" if ponderado else "")
            linha[v] = "sem anúncios" if c["n"] == 0 else (
                f"{nf(c['valor'])} [{nf(c['baixo'])}; {nf(c['alto'])}] ({ne})" + (" ⚠" if c["neff"] < MIN_N else ""))
        det.append(linha)
pd.DataFrame(det).set_index(["Medida", "Período"])
''')
com("c2")

md("""
## 3. Gráficos: uma medida por painel, uma linha por visão
Valor e IC de 95% por período. **Círculo aberto** = n ou n efetivo < 30. Visões que não se aplicam à medida não aparecem.
""")
code('''
CORES = {"Bruta": "#0072B2", "Ajustada": "#D55E00", "Só JC": "#009E73", "Ajustada + JC": "#CC79A7"}
fig, eixos = plt.subplots(3, 3, figsize=(13, 10))
for ax, n in zip(eixos.ravel(), nomes_ok):
    ax.set_title(n, fontsize=9, loc="left")
    if not RES[n]:
        ax.text(0.5, 0.5, "tema ausente", ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        continue
    for k, v in enumerate(VISOES):
        r = RES[n].get(v)
        if r is None:
            continue
        xs, ys, lo, hi = [], [], [], []
        for i, p in enumerate(PERIODOS):
            c = r["por"][p]
            if c["n"] == 0:
                continue
            x = i + (k - 1.5) * 0.09
            xs.append(x); ys.append(c["valor"]); lo.append(c["valor"] - c["baixo"]); hi.append(c["alto"] - c["valor"])
            ax.errorbar(x, c["valor"], yerr=[[max(lo[-1], 0)], [max(hi[-1], 0)]], fmt="o", color=CORES[v], capsize=2, ms=4,
                        mfc="white" if c["neff"] < MIN_N else CORES[v])
        ax.plot(xs, ys, color=CORES[v], lw=1, alpha=0.8, label=v)
    ax.set_xticks(range(len(PERIODOS)))
    ax.set_xticklabels([p.replace("antes de ", "<") for p in PERIODOS], fontsize=8)
    ax.set_ylabel(RES[n]["Bruta"] and MEDIDAS[nomes_ok.index(n)][2]); ax.set_xlim(-0.5, len(PERIODOS) - 0.5)
    ax.set_xlabel(f"mantém? {mantem(n)}", fontsize=8)
eixos[0, 0].legend(fontsize=7, frameon=False)
fig.suptitle("Valor e IC de 95% por período legal, em quatro visões (círculo aberto = n ou n efetivo < 30)")
fig.tight_layout(); plt.show()
''')

md("## 4. O que sobrevive e o que não")
md(COM.get("c3", "_(a preencher)_"))

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
