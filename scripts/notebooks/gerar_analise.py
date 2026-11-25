import json, sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "analise_descritiva.ipynb"
JC = Path(__file__).with_name("comentarios.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Análise descritiva dos anúncios

Este notebook responde a uma pergunta simples: **o que já temos no banco e o que ele permite dizer?**
Tudo é lido do banco compartilhado do grupo (view `anuncios_completos`), na versão de campos `{config.VERSAO_CAMPOS}`, e só entram
anúncios **relevantes** (tudo que não é do tipo `outro`).

Cada gráfico vem com uma ou duas frases dizendo o que ele mostra. Os números citados nessas frases foram lidos
da saída da própria execução. Se o banco crescer e você rodar de novo, **os gráficos mudam e os textos podem
ficar desatualizados**: confira os números.

> **Cuidado ao ler:** os anúncios foram achados por **frases de busca** (por exemplo, `"preta com leite"`),
> não por sorteio. Então o que aparece aqui descreve **o que a busca encontrou**, não o conjunto de todos os
> anúncios do século XIX. A seção 8 explica os limites.
""")

md("## Preparação: ler o banco\nO banco devolve no máximo 1000 linhas por consulta, então lemos em blocos (paginação) e juntamos tudo numa tabela do pandas.")
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

db = BancoSupabase().cliente      # lê o config/.env pelo módulo hdb

def ler_tudo(consulta, bloco=1000):
    """Executa a consulta em blocos de 1000 linhas e junta o resultado."""
    linhas, inicio = [], 0
    while True:
        parte = consulta().range(inicio, inicio + bloco - 1).execute().data
        linhas += parte
        if len(parte) < bloco:
            return pd.DataFrame(linhas)
        inicio += bloco

COLUNAS = ("id,bib,acervo,ano,pagina_fisica,periodo_legal,c_tipo,c_sexo,c_idade_min,c_idade_max,"
           "c_nacoes,c_condicao,c_recompensa,c_valor")
df = ler_tudo(lambda: db.table("anuncios_completos").select(COLUNAS)
              .eq("versao", config.VERSAO_ANUNCIOS).eq("c_versao", config.VERSAO_CAMPOS)
              .neq("c_tipo", "outro").order("id"))
print(f"{len(df)} anúncios relevantes (versão de anúncios {config.VERSAO_ANUNCIOS}, campos {config.VERSAO_CAMPOS})")
if len(df) != __N_COM__:
    print(f"ATENÇÃO: os comentários deste caderno foram escritos para __N_COM__ anúncios e agora são {len(df)}: "
          "confira os números dos textos antes de usar.")
''')
code('''
# Nomes curtos e em português para os gráficos
PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
def periodo_curto(p):
    return p if p.startswith("antes") else p.split(" ")[0]
df["periodo"] = pd.Categorical(df["periodo_legal"].map(periodo_curto), categories=PERIODOS, ordered=True)

TIPOS = ["fuga", "venda", "aluguel", "ama_de_leite", "compra"]
ROTULO_TIPO = {"fuga": "Fuga", "venda": "Venda", "aluguel": "Aluguel", "ama_de_leite": "Ama de leite", "compra": "Compra"}
df["tipo"] = pd.Categorical(df["c_tipo"], categories=TIPOS, ordered=True)

# Paleta que se distingue bem também para daltonismo (Okabe-Ito)
COR = {"fuga": "#D55E00", "venda": "#0072B2", "aluguel": "#009E73", "ama_de_leite": "#CC79A7", "compra": "#E69F00",
       "f": "#CC79A7", "m": "#0072B2", "ambos": "#009E73", "não diz": "#999999",
       "escravizado": "#D55E00", "forro": "#009E73", "livre": "#0072B2", "desconhecida": "#999999", "sem informação": "#DDDDDD"}
plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

def barras_empilhadas(tab, cores, titulo, xlabel, ylabel, proporcao=False, n_topo=None, largura=7.5):
    """tab: linhas = barras no eixo x, colunas = categorias empilhadas."""
    fig, ax = plt.subplots(figsize=(largura, 4.2))
    base = np.zeros(len(tab))
    for col in tab.columns:
        vals = tab[col].values.astype(float)
        ax.bar(range(len(tab)), vals, bottom=base, label=str(col), color=cores.get(col, None), edgecolor="white", linewidth=0.6)
        base += vals
    ax.set_xticks(range(len(tab)))
    ax.set_xticklabels([str(i) for i in tab.index])
    ax.set_title(titulo); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    if n_topo is not None:
        for i, n in enumerate(n_topo):
            ax.text(i, base[i] + (0.01 if proporcao else base.max() * 0.01), f"n = {n}", ha="center", va="bottom", fontsize=9)
        ax.set_ylim(0, base.max() * 1.1)
    ax.legend(title=None, frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout(); plt.show()
''')

# 1
md("## 1. Quanto temos\nQuantos anúncios relevantes existem em cada período legal, e de que tipo são.")
code('''
t1 = pd.crosstab(df["periodo"], df["tipo"])
t1.columns = [ROTULO_TIPO[c] for c in t1.columns]
t1["Total"] = t1.sum(axis=1)
t1.loc["Total"] = t1.sum()
t1
''')
code('''
graf = pd.crosstab(df["periodo"], df["tipo"])
graf.columns = [ROTULO_TIPO[c] for c in graf.columns]
cores1 = {ROTULO_TIPO[k]: COR[k] for k in TIPOS}
barras_empilhadas(graf, cores1, "Anúncios relevantes por período legal e tipo", "Período legal", "Número de anúncios",
                  n_topo=graf.sum(axis=1).astype(int).tolist())
''')
com("c1")

# 2
md("""
## 2. Sexo da pessoa anunciada
A coluna `c_sexo` tem `f`, `m`, `ambos` (o anúncio fala de mais de uma pessoa) ou vazio (**não diz**).
Abaixo, a **proporção** em cada grupo.

> **Aviso:** essa proporção vem das **frases de busca**, não da população. Buscamos, por exemplo, "preta com leite"
> (que só pode ser mulher) e "escravo fugido". Os grupos de ama de leite e de aluguel são
> dominados por mulheres *por causa do que procuramos*, não porque a população era assim.
""")
code('''
df["sexo"] = df["c_sexo"].fillna("não diz")
SEXOS = ["f", "m", "ambos", "não diz"]
ROT_SEXO = {"f": "Feminino", "m": "Masculino", "ambos": "Ambos", "não diz": "Não diz"}
cores_sexo = {ROT_SEXO[k]: COR[k] for k in SEXOS}

def prop_sexo(coluna):
    t = pd.crosstab(df[coluna], df["sexo"]).reindex(columns=SEXOS, fill_value=0)
    n = t.sum(axis=1)
    p = t.div(n, axis=0)
    p.columns = [ROT_SEXO[c] for c in p.columns]
    return p, n

p_per, n_per = prop_sexo("periodo")
p_tipo, n_tipo = prop_sexo("tipo")
print("Sexo por período (%):"); print((p_per * 100).round(1).assign(n=n_per))
print("\\nSexo por tipo (%):"); print((p_tipo * 100).round(1).assign(n=n_tipo))
''')
code('''
barras_empilhadas(p_per, cores_sexo, "Sexo por período legal (proporção)", "Período legal", "Proporção dos anúncios",
                  proporcao=True, n_topo=n_per.astype(int).tolist())
''')
code('''
p_tipo.index = [ROTULO_TIPO[i] for i in p_tipo.index]
barras_empilhadas(p_tipo, cores_sexo, "Sexo por tipo de anúncio (proporção)", "Tipo de anúncio", "Proporção dos anúncios",
                  proporcao=True, n_topo=n_tipo.astype(int).tolist())
''')
com("c2")

# 3
md("""
## 3. Idade
Nem todo anúncio diz a idade. Primeiro, quantos dizem. Depois, as faixas: **até 12**, **13–20**, **21–35** e **36 ou mais**.
Quando o anúncio dá um intervalo ("de 20 a 25 anos"), usamos o ponto médio.
""")
code('''
df["idade"] = df[["c_idade_min", "c_idade_max"]].astype(float).mean(axis=1)
tem = df["idade"].notna()
resumo = pd.DataFrame({"anúncios": df.groupby("periodo", observed=True).size(),
                       "com idade": df[tem].groupby("periodo", observed=True).size()}).fillna(0).astype(int)
resumo["% com idade"] = (resumo["com idade"] / resumo["anúncios"] * 100).round(1)
resumo.loc["Total"] = [len(df), int(tem.sum()), round(tem.mean() * 100, 1)]
resumo
''')
code('''
FAIXAS = ["até 12", "13–20", "21–35", "36+"]
df["faixa"] = pd.cut(df["idade"], bins=[-1, 12, 20, 35, 200], labels=FAIXAS)
t3 = pd.crosstab(df["periodo"], df["faixa"]).reindex(columns=FAIXAS, fill_value=0)
print(t3)
cores3 = dict(zip(FAIXAS, ["#E69F00", "#56B4E9", "#0072B2", "#D55E00"]))
barras_empilhadas(t3, cores3, "Faixas de idade por período legal (só anúncios com idade)", "Período legal",
                  "Número de anúncios com idade", n_topo=t3.sum(axis=1).astype(int).tolist())
''')
com("c3")

# 4
md("""
## 4. Nações africanas mais citadas
A coluna `c_nacoes` é uma **lista** (um anúncio pode citar mais de uma). "Nação" aqui é o termo usado no anúncio
(Benguela, Mina, Congo…), que dizia de onde vinha ou a que grupo era associada a pessoa; não é uma identidade que ela
mesma escolheu. Contamos quantos anúncios citam cada nação e mostramos as 8 mais citadas em cada período.
""")
code('''
nac = df[["periodo", "c_nacoes"]].explode("c_nacoes").dropna(subset=["c_nacoes"])
com_nacao = df[df["c_nacoes"].map(len) > 0].groupby("periodo", observed=True).size()
print("Anúncios que citam alguma nação, por período:"); print(com_nacao.reindex(PERIODOS, fill_value=0).to_dict())
top = nac["c_nacoes"].value_counts()
print("\\nNações no total:", len(top))
fig, eixos = plt.subplots(1, 4, figsize=(15, 4.2))
for ax, per in zip(eixos, PERIODOS):
    c = nac[nac["periodo"] == per]["c_nacoes"].value_counts().head(8)
    if len(c) == 0:
        ax.text(0.5, 0.5, "nenhuma nação\\ncitada", ha="center", va="center", transform=ax.transAxes); ax.set_axis_off()
    else:
        ax.barh(c.index[::-1], c.values[::-1], color="#0072B2")
        for y, v in enumerate(c.values[::-1]):
            ax.text(v + 0.1, y, str(v), va="center", fontsize=9)
    ax.set_title(f"{per}\\n(n = {int(com_nacao.get(per, 0))} anúncios)", fontsize=10)
    ax.set_xlabel("Anúncios que citam")
fig.suptitle("Nações africanas mais citadas por período (top 8)")
fig.tight_layout(); plt.show()
for per in PERIODOS:
    print(per, nac[nac["periodo"] == per]["c_nacoes"].value_counts().head(8).to_dict())
''')
com("c4")

# 5
md("""
## 5. Condição da pessoa
`c_condicao` diz se o anúncio trata a pessoa como **escravizada**, **forra**, **livre** ou se **não dá para saber** (desconhecida).
Em branco, o programa não achou nenhuma palavra de condição ("sem informação").
""")
code('''
df["condicao"] = df["c_condicao"].fillna("sem informação")
CONDS = ["escravizado", "forro", "livre", "desconhecida", "sem informação"]
t5 = pd.crosstab(df["tipo"], df["condicao"]).reindex(columns=CONDS, fill_value=0)
n5 = t5.sum(axis=1)
p5 = t5.div(n5, axis=0)
print("Contagens:"); print(t5.assign(total=n5))
print("\\nProporção (%):"); print((p5 * 100).round(1))
p5.index = [ROTULO_TIPO[i] for i in p5.index]
barras_empilhadas(p5, {k: COR[k] for k in CONDS}, "Condição por tipo de anúncio (proporção)", "Tipo de anúncio",
                  "Proporção dos anúncios", proporcao=True, n_topo=n5.astype(int).tolist())
''')
com("c5")

# 6
md("""
## 6. Recompensa nas fugas
Anúncios de fuga costumam oferecer **gratificação** a quem capturasse a pessoa. `c_recompensa` marca se o anúncio a menciona
e `c_valor` guarda o valor, **como aparece no texto** (e lido por OCR, então pode ter erro).
""")
code('''
fu = df[df["c_tipo"] == "fuga"]
t6 = fu.groupby("periodo", observed=True).agg(fugas=("id", "size"), com_recompensa=("c_recompensa", "sum"))
t6["com_recompensa"] = t6["com_recompensa"].astype(int)
t6["% com recompensa"] = (t6["com_recompensa"] / t6["fugas"] * 100).round(1)
t6.loc["Total"] = [len(fu), int(fu["c_recompensa"].sum()), round(fu["c_recompensa"].mean() * 100, 1)]
print(t6)
print("\\nRecompensa em anúncios que NÃO são fuga:", int(df[df["c_tipo"] != "fuga"]["c_recompensa"].sum()))
print("Fugas com valor lido:", int(fu["c_valor"].notna().sum()))
fu[fu["c_valor"].notna()][["id", "ano", "c_valor"]]
''')
code('''
g = t6.drop("Total")
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(range(len(g)), g["% com recompensa"], color="#D55E00")
for i, (pct, n, k) in enumerate(zip(g["% com recompensa"], g["fugas"], g["com_recompensa"])):
    ax.text(i, pct + 0.8, f"{pct:.0f}%\\n({k} de {n})", ha="center", va="bottom", fontsize=9)
ax.set_xticks(range(len(g))); ax.set_xticklabels(g.index)
ax.set_ylim(0, max(g["% com recompensa"].max() * 1.3, 10))
ax.set_title("Fugas que oferecem recompensa, por período"); ax.set_xlabel("Período legal"); ax.set_ylabel("% das fugas")
fig.tight_layout(); plt.show()
''')
com("c6")

# 7
md("""
## 7. Densidade: anúncios relevantes por página
Cada acervo (jornal e década) tem páginas de qualidade e tamanho diferentes, e nós só lemos páginas que a busca apontou.
Dividimos o número de anúncios relevantes pelo número de páginas lidas (`status = ok`) para ver o efeito de cada acervo.
""")
code('''
pg = ler_tudo(lambda: db.table("paginas").select("id,bib,ano").eq("status", "ok").order("id"))
paginas_bib = pg.groupby("bib").size().rename("páginas lidas")
rel_bib = df.groupby("bib").size().rename("anúncios relevantes")
nome_bib = df.drop_duplicates("bib").set_index("bib")["acervo"].rename("acervo")
t7 = pd.concat([paginas_bib, rel_bib], axis=1).join(nome_bib).fillna({"anúncios relevantes": 0})
t7["anúncios relevantes"] = t7["anúncios relevantes"].astype(int)
t7["por página"] = (t7["anúncios relevantes"] / t7["páginas lidas"]).round(2)
t7 = t7.sort_values("acervo")
t7.loc["Total"] = [t7["páginas lidas"].sum(), t7["anúncios relevantes"].sum(), "",
                   round(t7["anúncios relevantes"].sum() / t7["páginas lidas"].sum(), 2)]
t7
''')
code('''
g = t7.drop("Total").dropna(subset=["acervo"])
g = g[g["páginas lidas"] > 0]
rot = g["acervo"].str.replace(" (RJ)", "", regex=False).str.replace("Jornal do Commercio", "JC").str.replace("Diário do Rio de Janeiro", "Diário do RJ").str.replace("Imperio do Brasil: Diario Fluminense", "Diário Fluminense")
fig, ax = plt.subplots(figsize=(8, 4.2))
y = range(len(g))
ax.barh(list(y), g["por página"].astype(float), color="#0072B2")
for i, (v, n, p) in enumerate(zip(g["por página"].astype(float), g["anúncios relevantes"], g["páginas lidas"])):
    ax.text(v + 0.05, i, f"{v:.2f}  ({n} anúncios em {p} páginas)", va="center", fontsize=8.5)
ax.set_yticks(list(y)); ax.set_yticklabels(rot); ax.invert_yaxis()
ax.set_xlim(0, g["por página"].astype(float).max() * 1.9)
ax.set_title("Anúncios relevantes por página lida, por acervo"); ax.set_xlabel("Anúncios relevantes por página"); ax.set_ylabel("Acervo")
fig.tight_layout(); plt.show()
''')
com("c7")

# 8
md("""
## 8. O que não podemos concluir
""")
code('''
# Números de apoio para a lista abaixo
d80 = df[df["periodo"] == "1871–1888"]
print("1871–1888: anos presentes e anúncios por ano:", d80["ano"].value_counts().sort_index().to_dict())
print("Antes de 1831 por acervo:", df[df["periodo"] == "antes de 1831"]["acervo"].value_counts().to_dict())
alu = d80[d80["c_tipo"] == "aluguel"]
print("Aluguéis 1871–1888:", len(alu), "| condição:", alu["condicao"].value_counts().to_dict())
print("Anúncios por década de acervo (1870 a 1879 vs 1880 a 1889):", df["acervo"].value_counts().to_dict())
''')
com("c8")

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gerado", SAIDA)
