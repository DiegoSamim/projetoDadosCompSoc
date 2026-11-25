import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "equilibrio_periodos.ipynb"
JC = Path(__file__).with_name("comentarios_equilibrio.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Tópicos com períodos do mesmo tamanho

Este caderno responde: **a mudança dos temas entre os períodos legais é real ou é efeito de os períodos terem tamanhos diferentes?**
Os períodos têm muito mais anúncios uns que outros, e o modelo de tópicos (LDA) aprende mais dos períodos grandes.
Aqui **sorteamos o mesmo número `n` de anúncios por período**, ajustamos o LDA, damos nome aos temas e repetimos 10 vezes
(sementes 0 a 9). Comparamos o resultado com o modelo atual (`{config.VERSAO_TOPICOS}`, corpus `{config.VERSAO_CORPUS}`).

Os números dos comentários foram lidos da saída da própria execução; se o banco mudar, **confira os números de novo**.

> **Cuidado ao ler:** os anúncios foram achados por **frases de busca**, não por sorteio, e os nomes dos temas são
> **hipóteses do grupo**. O sorteio aqui é só para igualar os períodos.
""")

md("## Preparação: ler o corpus e o modelo atual")
code('''
import sys
from pathlib import Path

RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from hdb import config
from hdb.banco import BancoSupabase
from hdb.topicos import equilibrado, nomear

pd.set_option("display.width", 200)
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

corpus = pd.DataFrame(banco.anuncios_do_corpus(config.VERSAO_CORPUS))
corpus = corpus[corpus["texto_padrao"].fillna("").str.strip() != ""]
corpus["periodo"] = corpus["periodo_legal"].map(lambda p: periodo_curto(p) if isinstance(p, str) else None)
corpus = corpus[corpus["periodo"].isin(PERIODOS)]
print(f"{len(corpus)} anúncios no corpus {config.VERSAO_CORPUS} com período legal")
if len(corpus) != __N_COM__:
    print(f"ATENÇÃO: os comentários deste caderno foram escritos para __N_COM__ anúncios e agora são {len(corpus)}: "
          "confira os números dos textos antes de usar.")

plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
''')

md("""
## 1. Quantos anúncios por período e qual `n`
`n` é o **tamanho do menor período grande** (entre os que têm pelo menos 200 anúncios). Cada sorteio pega `n` anúncios
de cada período. Quem tem menos de `n` (por exemplo, "antes de 1831") entra **inteiro** e fica **marcado**: o resultado
desse período é menos firme e ele pesa menos no modelo.
""")
code('''
tamanho = corpus.groupby("periodo").size().reindex(PERIODOS, fill_value=0)
grandes = tamanho[tamanho >= 200]
N = int(grandes.min())
usado = tamanho.clip(upper=N)
aviso = ["" if t >= N else "ENTRA INTEIRO (menos de n)" for t in tamanho]
if N < 30:
    print(f"ATENÇÃO: n = {N} é menor que 30: o resultado é muito frágil.")
print(f"n = {N} (menor período com pelo menos 200 anúncios: {grandes.idxmin()})")
pd.DataFrame({"anúncios no corpus": tamanho, "usados por sorteio": usado, "aviso": aviso})
''')
com("c1")

md("""
## 2. O modelo atual
Os temas e as proporções médias por período do modelo já gravado no banco (sem equilíbrio). Os nomes vêm de
`hdb.topicos.nomear`, o mesmo critério do caderno de tópicos.
""")
code(f'''
MODELO = config.VERSAO_TOPICOS
pal = ler_tudo(lambda: db.table("topico_palavras").select("topico,palavra,peso").eq("versao", MODELO)
               .order("topico").order("peso", desc=True))
dist = ler_tudo(lambda: db.table("anuncio_topicos").select("anuncio_id,topico,proporcao").eq("versao", MODELO)
                .order("anuncio_id").order("topico"))
K = pal["topico"].nunique()
NOMES = nomear({{t: g.sort_values("peso", ascending=False)["palavra"].head(12) for t, g in pal.groupby("topico")}})
pivo = dist.pivot(index="anuncio_id", columns="topico", values="proporcao")
atual = corpus.set_index("id")[["periodo"]].join(pivo, how="inner")
atual_media = atual.groupby("periodo")[list(pivo.columns)].mean().reindex(PERIODOS).T
atual_media.index = [NOMES[t] for t in atual_media.index]
print(f"modelo {{MODELO}}: {{K}} temas, {{len(atual)}} anúncios")
(atual_media * 100).round(1)
''')

md("""
## 3. Os 10 sorteios com períodos do mesmo tamanho
Para cada sorteio, o LDA é ajustado do zero com **o mesmo número de temas do modelo atual**, os temas são nomeados e
medimos a proporção média de cada tema em cada período. Como os temas são nomeados por palavras de referência, um
tema pode **não aparecer** em algum sorteio (a média usa só os sorteios em que ele apareceu) e temas sem nome ficam de fora.
""")
code('''
textos_por_periodo = {p: g["texto_padrao"].tolist() for p, g in corpus.groupby("periodo") if p in PERIODOS}
textos_por_periodo = {p: textos_por_periodo[p] for p in PERIODOS if p in textos_por_periodo}
r = equilibrado(textos_por_periodo, N, sorteios=10, n_topicos=K)
print("anúncios usados por período:", r["n_usado"])
print("períodos com menos de n (entraram inteiros):", r["curtos"])
print(f"temas sem nome nos 10 sorteios: {r['sem_nome']} (por sorteio: {r['sem_nome_por_sorteio']})")
n_aparece = {nome: sum(1 for s in r["sorteios"] if nome in s) for nome in r["media"]}
print("em quantos dos 10 sorteios cada tema apareceu:", n_aparece)
''')

md("""
## 4. Tabela: períodos iguais × modelo atual
Cada célula mostra a **proporção média (%)** do tema no período: primeiro a média dos sorteios com períodos iguais
(entre parênteses, o mínimo e o máximo dos sorteios), depois a do modelo atual. Uma diferença grande entre as duas
sugere que o tamanho do período estava mexendo no resultado. **Período marcado com `*` entrou inteiro (n menor que `n`).**
""")
code('''
rot_p = {p: (p + " *" if p in r["curtos"] else p) for p in PERIODOS}
nomes_ord = list(r["media"])
linhas = []
for nome in nomes_ord:
    linha = {"Tema": nome}
    for p in PERIODOS:
        m, lo, hi = (100 * r[k][nome][p] for k in ("media", "minimo", "maximo"))
        a = 100 * atual_media.loc[nome, p] if nome in atual_media.index else float("nan")
        linha[rot_p[p]] = f"{m:.1f} ({lo:.1f}–{hi:.1f}) | atual {a:.1f}"
    linhas.append(linha)
pd.DataFrame(linhas).set_index("Tema")
''')
code('''
# Só as médias, em % (equilibrado, atual e diferença), para ler os números com mais facilidade
eq = pd.DataFrame(r["media"]).T.reindex(columns=PERIODOS) * 100
dif = (eq - (atual_media.reindex(eq.index) * 100)).round(1)
print("Período do mesmo tamanho (%):"); print(eq.round(1).to_string())
print("\\nDiferença (equilibrado - atual), pontos percentuais:"); print(dif.to_string())
''')
com("c4")

md("""
## 5. Gráfico: o tema por período
Uma linha cheia é a **média dos sorteios** (a faixa vai do mínimo ao máximo); a linha tracejada é o **modelo atual**.
Se a linha cheia e a tracejada contam a mesma história, o tamanho do período não explica a mudança.
""")
code('''
CORES = ["#0072B2", "#D55E00", "#E69F00", "#009E73", "#CC79A7", "#999999", "#56B4E9", "#F0E442"]
temas = list(r["media"])
colunas = 3
linhas_g = max(1, -(-len(temas) // colunas))
fig, eixos = plt.subplots(linhas_g, colunas, figsize=(13, 3.2 * linhas_g), sharex=True, squeeze=False)
x = np.arange(len(PERIODOS))
for i, nome in enumerate(temas):
    ax = eixos[i // colunas][i % colunas]
    cor = CORES[i % len(CORES)]
    m = np.array([r["media"][nome][p] for p in PERIODOS]) * 100
    lo = np.array([r["minimo"][nome][p] for p in PERIODOS]) * 100
    hi = np.array([r["maximo"][nome][p] for p in PERIODOS]) * 100
    ax.fill_between(x, lo, hi, color=cor, alpha=0.25)
    ax.plot(x, m, color=cor, marker="o", label="períodos iguais")
    if nome in atual_media.index:
        ax.plot(x, atual_media.loc[nome, PERIODOS].values * 100, color="black", ls="--", marker="s", ms=4, label="modelo atual")
    ax.set_title(nome if len(nome) < 38 else nome[:36] + "…", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([rot_p[p].replace(" ", "\\n", 1) if p.startswith("antes") else rot_p[p] for p in PERIODOS], fontsize=8)
    ax.set_ylabel("Proporção média (%)")
    if i == 0:
        ax.legend(frameon=False, fontsize=8)
for j in range(len(temas), linhas_g * colunas):
    eixos[j // colunas][j % colunas].set_axis_off()
fig.suptitle(f"Peso de cada tema por período, com {N} anúncios por período (10 sorteios; * = entrou inteiro)")
fig.tight_layout(); plt.show()
''')
com("c5")

md("""
## 6. O que isso diz e o que não diz
""")
md(COM.get("c6", "_(a preencher)_"))

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
