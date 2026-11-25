import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "mudanca_por_tipo.ipynb"
JC = Path(__file__).with_name("comentarios_tipos.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# O que muda ao longo do tempo dentro de cada tipo de anúncio

Este caderno responde: **dentro do mesmo tipo de anúncio (fuga, aluguel, venda, ama de leite), o que muda de um período legal para outro?**
Comparar períodos misturando os tipos engana, porque a composição dos tipos muda de período para período. Aqui cada tipo é lido sozinho.
Para cada tipo e período mostramos (a) as **10 palavras que mais distinguem aquele período dos outros do mesmo tipo** e (b) alguns **atributos** dos anúncios.

Corpus `{config.VERSAO_CORPUS}`, campos `{config.VERSAO_CAMPOS}`. Os números dos comentários foram lidos da saída da própria execução;
se o banco mudar, **confira os números de novo**.

> **Cuidado ao ler:** os anúncios foram achados por **frases de busca**, não por sorteio. **Grupos com menos de 30 anúncios
> aparecem marcados com `⚠`** (e em itálico/negrito nas tabelas de palavras): as diferenças ali são frágeis.
""")

md("""
## Como medimos as palavras que distinguem
Usamos o **log-odds ponderado com prior informativo** de Monroe, Colaresi e Quinn (2008). Para cada palavra, comparamos
quanto ela aparece no período contra quanto aparece nos **outros períodos do mesmo tipo**, e dividimos a diferença
(em log-odds) pelo seu desvio estimado, o que dá um **z-score**. O prior é proporcional à frequência da palavra no
conjunto inteiro do tipo, o que evita que palavras raras dominem. Só mostramos palavras com **z ≥ 1,96**, ordenadas por z;
a coluna entre parênteses é o número de vezes que a palavra aparece nos anúncios do período.
""")

md("## Preparação: ler o corpus e os campos")
code('''
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import numpy as np
import pandas as pd
from IPython.display import Markdown, display
from hdb import config
from hdb.banco import BancoSupabase
from hdb.distintivas import palavras_distintivas

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
MIN_N = 30

corpus = pd.DataFrame(banco.anuncios_do_corpus(config.VERSAO_CORPUS))
corpus = corpus[corpus["texto_padrao"].fillna("").str.strip() != ""]
# campos que o corpus não traz (nações, cores, ofícios, condição, recompensa, idade máxima), da view anuncios_completos
extra = ler_tudo(lambda: db.table("anuncios_completos").select("id,c_idade_max,c_nacoes,c_cores,c_oficios,c_recompensa")
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

TIPOS = [("fuga", "Fuga"), ("aluguel", "Aluguel"), ("venda", "Venda"), ("ama_de_leite", "Ama de leite")]
n_compra = int((df["c_tipo"] == "compra").sum())
if n_compra >= MIN_N:
    TIPOS.append(("compra", "Compra"))
print(f"Anúncios do tipo compra: {n_compra} ({'entra' if n_compra >= MIN_N else 'fica de fora: menos de 30'})")

def atributos(g, tipo):
    """Atributos de um grupo (um período dentro de um tipo)."""
    n = len(g)
    pct = lambda mask: round(100 * float(mask.sum()) / n, 1) if n else float("nan")
    linha = {"n": f"{n} ⚠" if n < MIN_N else str(n),
             "% feminino": pct(g["c_sexo"] == "f"),
             "% com idade": pct(g["idade"].notna()),
             "idade mediana": round(float(g["idade"].median()), 1) if g["idade"].notna().any() else float("nan"),
             "% com nação": pct(tem(g["c_nacoes"])),
             "% com ofício": pct(tem(g["c_oficios"])),
             "% com cor": pct(tem(g["c_cores"]))}
    if tipo == "fuga":
        linha["% com recompensa"] = pct(g["c_recompensa"].fillna(False).astype(bool))
    return linha
''')

md("""
## 1. Quantos anúncios por tipo e período
Os grupos com `⚠` têm menos de 30 anúncios.
""")
code('''
t1 = pd.crosstab(df["c_tipo"], df["periodo"]).reindex(columns=PERIODOS, fill_value=0)
t1["Total"] = t1.sum(axis=1)
t1.map(lambda v: f"{v} ⚠" if v < MIN_N else str(v))
''')
com("c1")

md("""
## 2. Palavras que distinguem cada período, dentro de cada tipo
Para cada tipo, as 10 palavras mais distintivas de cada período (z ≥ 1,96) em relação aos outros períodos **do mesmo tipo**.
Períodos com menos de 30 anúncios vêm com aviso: as palavras ali refletem poucos textos.
""")
code('''
PALAVRAS = {}
for tipo, rotulo in TIPOS:
    sub = df[df["c_tipo"] == tipo]
    contagens = {p: Counter(w for t in sub[sub["periodo"] == p]["texto_padrao"] for w in t.split()) for p in PERIODOS}
    contagens = {p: c for p, c in contagens.items() if c}   # períodos sem anúncio do tipo ficam de fora
    ns = sub.groupby("periodo").size()
    dist = palavras_distintivas(contagens, n=10)
    PALAVRAS[tipo] = dist
    linhas = []
    for p in PERIODOS:
        n = int(ns.get(p, 0))
        pal = ", ".join(f"{w} ({k})" for w, z, k in dist.get(p, [])) or "(nenhuma com z ≥ 1,96)"
        if n == 0:
            continue
        linhas.append(f"| {p} | {'**⚠ ' + str(n) + '**' if n < MIN_N else n} | {('**⚠ poucos anúncios:** ' + pal) if n < MIN_N else pal} |")
    display(Markdown(f"### {rotulo}\\n\\n| Período | n | Palavras distintivas (n no período) |\\n|---|---|---|\\n" + "\\n".join(linhas)))
''')
com("c2")

md("""
## 3. Atributos por período, dentro de cada tipo
% feminino, % com idade, idade mediana (só entre os que dizem a idade), % com nação, % com ofício, % com cor e, nas fugas,
% com recompensa. As porcentagens são sobre **todos** os anúncios do período naquele tipo. `n` com `⚠` = menos de 30 anúncios: não confie nas diferenças.
""")
code('''
for tipo, rotulo in TIPOS:
    sub = df[df["c_tipo"] == tipo]
    linhas = {p: atributos(sub[sub["periodo"] == p], tipo) for p in PERIODOS if (sub["periodo"] == p).any()}
    display(Markdown(f"### {rotulo}"))
    display(pd.DataFrame(linhas).T.rename_axis("Período"))
''')
com("c3")

md("""
## 4. O que isso diz e o que não diz
""")
md(COM.get("c4", "_(a preencher)_"))

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
