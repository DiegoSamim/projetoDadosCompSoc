import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "topicos_por_periodo.ipynb"
JC = Path(__file__).with_name("comentarios_topicos.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Tópicos por período legal

Este notebook responde: **sobre o que falam os anúncios, e isso muda ao longo do século XIX?**
Usamos o modelo de tópicos `{config.VERSAO_TOPICOS}` (corpus `{config.VERSAO_CORPUS}`, campos `{config.VERSAO_CAMPOS}`), já gravado no banco compartilhado do grupo.
O modelo antigo `t4` (6 tópicos) aparece só na seção 8, para comparação.


Cada gráfico vem com uma ou duas frases dizendo o que ele mostra. Os números dessas frases foram lidos da saída
da própria execução; se o banco mudar, **confira os números de novo**.

> **Cuidado ao ler:** os anúncios foram achados por **frases de busca**, não por sorteio. O que aparece aqui descreve
> o que a busca encontrou, não todos os anúncios do século XIX. Os **nomes** dos tópicos são **hipóteses do grupo**, não fatos.
""")

md("""
## 1. O que é um tópico e por que k = 6
**Um tópico é um grupo de palavras que costumam aparecer juntas nos mesmos anúncios.** O programa (LDA) não lê o sentido:
ele só agrupa palavras. Quem dá nome ao grupo somos nós, olhando as palavras e os anúncios.

**Por que 6 tópicos (k = 6)?** Rodamos o modelo várias vezes com sementes diferentes (ver `scripts/estabilidade_topicos.py`)
e medimos quantos tópicos **se repetem** (similaridade de cosseno ≥ 0,8). Com k = 4, 56% dos tópicos se repetem; com k = 6, 59%;
com k = 8, 50%; com k = 10, 29%; com k = 12, 44%. Não cai de forma regular, mas k = 10 é o pior. Mantemos k = 6 (e não k = 4) para separar mais temas. Mesmo em k = 8, quatro temas se repetem muito bem nas
sementes: fuga (0,93), serviço doméstico (0,90), ama de leite (0,85) e aluguel de homens (0,81).
**O resultado também depende da semente do sorteio:** com uma semente fixa, 3 anúncios a mais já reorganizaram todos os tópicos. Por isso usamos a semente mais representativa entre 10.
Ou seja, a estabilidade é **moderada**: os resultados abaixo são pistas, não medidas exatas.
""")

md("## Preparação: ler o banco\nO banco devolve no máximo 1000 linhas por consulta, então lemos em blocos (paginação).")
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

pd.set_option("display.max_colwidth", 200)
pd.set_option("display.width", 200)
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

MODELO = config.VERSAO_TOPICOS
COMPARA = "t4"
palavras = ler_tudo(lambda: db.table("topico_palavras").select("versao,topico,palavra,peso")
                    .in_("versao", [MODELO, COMPARA]).order("versao").order("topico").order("peso", desc=True))
dist = ler_tudo(lambda: db.table("anuncio_topicos").select("anuncio_id,topico,proporcao")
                .eq("versao", MODELO).order("anuncio_id").order("topico"))
anuncios = ler_tudo(lambda: db.table("anuncios_completos")
                    .select("id,periodo_legal,c_tipo,c_sexo,c_idade_min,c_idade_max,ano,texto")
                    .eq("versao", config.VERSAO_ANUNCIOS).eq("c_versao", config.VERSAO_CAMPOS).order("id"))
print(f"{dist['anuncio_id'].nunique()} anúncios no modelo {MODELO}; {len(anuncios)} anúncios com campos {config.VERSAO_CAMPOS} no banco")
''')
code('''
PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
def periodo_curto(p):
    return p if p.startswith("antes") else p.split(" ")[0]

# Nomes SUGERIDOS (provisórios): o grupo deve confirmar
# Nomes SUGERIDOS: o LDA numera os tópicos ao acaso (a cada rodada o T0 pode ser outro), então cada nome vem das
# palavras de referência abaixo: o tópico recebe o nome cujas palavras mais aparecem entre as suas 12 de maior peso.
REFERENCIAS = {
    "Fuga: nome, idade e dono": {"anos", "dia", "escravo", "idade", "tiver", "nome", "contra", "souber", "dias", "cor"},
    "Fuga: roupa levada e nação": {"levou", "nacao", "fugiu", "levar", "sera", "corrente", "dia", "preto"},
    "Ama de leite": {"leite", "ama", "meses", "carinhosa", "parto", "criancas", "parda"},
    "Serviço doméstico (aluguel e venda de mulheres)": {"lava", "cozinha", "engoma", "lavar", "engomar", "cozinhar", "servico", "aluga", "preta"},
    "Venda de moleques e pretos (lotes)": {"moleque", "pretos", "dois", "vendem", "pagem", "proprio", "cozinheiro"},
    "Venda com preço e qualidades": {"preco", "perfeito", "bonita", "pardo", "forno", "bem", "todo", "servico", "vende"},
}
from scipy.optimize import linear_sum_assignment
_topo = {t: set(g.sort_values("peso", ascending=False)["palavra"].head(12)) for t, g in palavras[palavras.versao == MODELO].groupby("topico")}
_ts, _nomes = sorted(_topo), list(REFERENCIAS)
_custo = [[-len(_topo[t] & REFERENCIAS[n]) for n in _nomes] for t in _ts]
NOMES = {_ts[i]: (_nomes[j] if -_custo[i][j] >= 2 else f"Tópico {_ts[i]} (sem nome)") for i, j in zip(*linear_sum_assignment(_custo))}
K = len(NOMES)
rot = lambda t: f"T{t} {NOMES[t]}"

# Uma linha por anúncio do modelo, com o tópico dominante
pivo = dist.pivot(index="anuncio_id", columns="topico", values="proporcao")
base = anuncios.drop_duplicates("id").set_index("id").join(pivo, how="inner")
base["dominante"] = base[list(range(K))].idxmax(axis=1)
base["periodo"] = pd.Categorical(base["periodo_legal"].map(periodo_curto), categories=PERIODOS, ordered=True)
print(len(base), "anúncios na base de análise")
if len(base) != __N_COM__:
    print(f"ATENÇÃO: os comentários deste caderno foram escritos para __N_COM__ anúncios e agora são {len(base)}: "
          "confira os números dos textos antes de usar.")

# Paleta Okabe-Ito, uma cor por tópico
CORES = ["#0072B2", "#D55E00", "#E69F00", "#009E73", "#CC79A7", "#999999"]
plt.rcParams.update({"figure.dpi": 110, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
''')

md(f"""
## 2. Os tópicos do modelo `{config.VERSAO_TOPICOS}`
Abaixo, as **12 palavras de maior peso** de cada tópico (as palavras estão sem acento, como no corpus padronizado).
A coluna **Nome sugerido** é uma **proposta provisória**: o grupo precisa confirmar ou trocar.
""")
code('''
tab = (palavras[palavras["versao"] == MODELO].groupby("topico")["palavra"].apply(lambda s: ", ".join(s.head(12))))
tabela = pd.DataFrame({"Nome sugerido": [NOMES[t] for t in tab.index], "12 palavras de maior peso": tab.values},
                      index=pd.Index(tab.index, name="Tópico"))
tabela
''')
com("c2")

md("""
## 3. Os 3 anúncios mais típicos de cada tópico
São os 3 com **maior proporção** daquele tópico. Mostramos os primeiros 250 caracteres do texto original.
Serve para conferir se o nome sugerido faz sentido.
""")
code('''
for t in range(K):
    print(f"=== Tópico {t}: {NOMES[t]} ===")
    top3 = base.sort_values(t, ascending=False).head(3)
    for i, r in top3.iterrows():
        txt = " ".join(str(r["texto"]).split())[:250]
        print(f"  [id {i}, {r['periodo']}, tipo {r['c_tipo']}, proporção {r[t]:.2f}] {txt}")
    print()
''')
com("c3")

md("""
## 4. Peso de cada tópico por período legal
Para cada período, a **proporção média** de cada tópico nos anúncios daquele período (cada coluna soma 100%).
""")
code('''
media = base.groupby("periodo", observed=True)[list(range(K))].mean().reindex(PERIODOS)
n_per = base.groupby("periodo", observed=True).size().reindex(PERIODOS)
med = (media * 100).round(1)
med.columns = [rot(t) for t in med.columns]
print(med.assign(n=n_per).to_string())
print("\\nComposição por tipo em cada período (% dos anúncios):")
print((pd.crosstab(base["periodo"], base["c_tipo"], normalize="index") * 100).round(1).to_string())

fig, ax = plt.subplots(figsize=(8, 4.5))
fundo = np.zeros(len(PERIODOS))
for t in range(K):
    ax.bar(range(len(PERIODOS)), media[t].values * 100, bottom=fundo, color=CORES[t], edgecolor="white", label=rot(t))
    fundo += media[t].values * 100
ax.set_xticks(range(len(PERIODOS)))
ax.set_xticklabels([f"{p}\\n(n = {n_per[p]})" for p in PERIODOS])
ax.set_title("Peso médio de cada tópico por período legal")
ax.set_xlabel("Período legal"); ax.set_ylabel("Proporção média do tópico (%)")
ax.legend(frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
fig.tight_layout(); plt.show()
''')
com("c4")

md("""
## 5. Por sexo
Aqui o tópico entra como **proporção média** entre os anúncios de cada sexo (`f` ou `m`).

> **Ressalva:** o sexo vem de **palavras do anúncio** ("preta", "preto", "moleque"…), e o tipo "ama de leite" é feminino
> **por construção**. Por isso, depois do gráfico, cruzamos **tipo × sexo** e **tipo × tópico** para separar o que
> é efeito do tipo.
""")
code('''
sx = base[base["c_sexo"].isin(["f", "m"])]
n_sx = sx.groupby("c_sexo").size()
m_sx = sx.groupby("c_sexo")[list(range(K))].mean().T * 100
m_sx.index = [rot(t) for t in m_sx.index]
m_sx = m_sx.rename(columns={"f": "Feminino", "m": "Masculino"})
print((n_sx.rename({"f": "Feminino", "m": "Masculino"})).to_dict())
print(m_sx.round(1).to_string())

fig, ax = plt.subplots(figsize=(8, 4.5))
y = np.arange(K); h = 0.38
ax.barh(y - h/2, m_sx["Feminino"].values, h, color="#CC79A7", label=f"Feminino (n = {n_sx.get('f', 0)})")
ax.barh(y + h/2, m_sx["Masculino"].values, h, color="#0072B2", label=f"Masculino (n = {n_sx.get('m', 0)})")
ax.set_yticks(y); ax.set_yticklabels(m_sx.index); ax.invert_yaxis()
ax.set_title("Peso médio de cada tópico, por sexo"); ax.set_xlabel("Proporção média do tópico (%)"); ax.set_ylabel("Tópico")
ax.legend(frameon=False)
fig.tight_layout(); plt.show()
''')
code('''
# O sexo é efeito do tipo? Tipo x sexo (contagem) e tipo x tópico médio (%)
print(pd.crosstab(base["c_tipo"], base["c_sexo"].fillna("não diz")).to_string())
print()
por_tipo = base.groupby("c_tipo")[list(range(K))].mean() * 100
por_tipo.columns = [f"T{t}" for t in por_tipo.columns]
print(por_tipo.round(1).assign(n=base.groupby("c_tipo").size()).to_string())
print()
# Dentro de um mesmo tipo, f e m diferem? (fuga e venda são os tipos com os dois sexos)
for tipo in ["fuga", "venda"]:
    s = sx[sx["c_tipo"] == tipo]
    if s["c_sexo"].nunique() == 2:
        d = (s.groupby("c_sexo")[list(range(K))].mean() * 100).round(1)
        d.columns = [f"T{t}" for t in d.columns]
        print(f"Tipo {tipo}: n =", s.groupby("c_sexo").size().to_dict()); print(d.to_string()); print()
''')
com("c5")

md("""
## 6. Por faixa de idade
Só entram anúncios que **dizem a idade** (usamos o ponto médio quando há intervalo). O número é pequeno,
então **as diferenças entre faixas são frágeis**: veja o `n` de cada linha antes de tirar conclusões.
""")
code('''
base["idade"] = base[["c_idade_min", "c_idade_max"]].astype(float).mean(axis=1)
FAIXAS = ["até 12", "13–20", "21–35", "36+"]
base["faixa"] = pd.cut(base["idade"], bins=[-1, 12, 20, 35, 200], labels=FAIXAS)
com_idade = base[base["idade"].notna()]
print(f"{len(com_idade)} de {len(base)} anúncios têm idade")
ti = com_idade.groupby("faixa", observed=True)[list(range(K))].mean() * 100
ti.columns = [f"T{t}" for t in ti.columns]
ti.insert(0, "n", com_idade.groupby("faixa", observed=True).size())
ti.round(1)
''')
com("c6")

md("""
## 7. Tópico × tipo de anúncio
Cada anúncio vai para o seu **tópico dominante** (o de maior proporção). A matriz conta quantos anúncios de cada tipo
caem em cada tópico. Se cada tópico fosse "só" um tipo, haveria um bloco forte por coluna.
""")
code('''
tt = pd.crosstab(base["c_tipo"], base["dominante"])
tt.columns = [f"T{t}" for t in tt.columns]
tt["Total"] = tt.sum(axis=1)
tt.loc["Total"] = tt.sum()
print(tt.to_string())

mat = pd.crosstab(base["c_tipo"], base["dominante"]).reindex(columns=range(K), fill_value=0)
fig, ax = plt.subplots(figsize=(8.5, 3.8))
im = ax.imshow(mat.values, cmap="Blues", aspect="auto")
ax.set_xticks(range(K)); ax.set_xticklabels([f"T{t}\\n{NOMES[t][:22]}" for t in range(K)], fontsize=8)
ax.set_yticks(range(len(mat))); ax.set_yticklabels(mat.index)
for i in range(mat.shape[0]):
    for j in range(K):
        v = mat.values[i, j]
        ax.text(j, i, str(v), ha="center", va="center", color="white" if v > mat.values.max() * 0.5 else "black")
ax.set_title("Anúncios por tipo e tópico dominante"); ax.set_xlabel("Tópico dominante"); ax.set_ylabel("Tipo de anúncio")
fig.colorbar(im, ax=ax, label="Número de anúncios")
fig.tight_layout(); plt.show()
''')
com("c7")

md(f"""
## 8. Comparação com o modelo `t4`
Para cada tópico de `t4`, buscamos o tópico de `{config.VERSAO_TOPICOS}` mais parecido pela **similaridade de cosseno** entre as distribuições de palavras.

> **Aproximação:** o banco guarda só as **12 palavras de maior peso** de cada tópico. Usamos a união dessas palavras
> como vocabulário e **peso 0** para as ausentes. O resultado é aproximado e ignora a cauda de cada tópico.
""")
code('''
pal = palavras.pivot_table(index=["versao", "topico"], columns="palavra", values="peso", fill_value=0)
M2, M3 = pal.loc[COMPARA], pal.loc[MODELO]
vocab = sorted(set(M2.columns) | set(M3.columns))
A = M2.reindex(columns=vocab, fill_value=0).values
B = M3.reindex(columns=vocab, fill_value=0).values
cos = (A / np.linalg.norm(A, axis=1, keepdims=True)) @ (B / np.linalg.norm(B, axis=1, keepdims=True)).T
linhas = []
for i, antigo in enumerate(M2.index):
    j = int(cos[i].argmax())
    linhas.append({"Tópico do modelo antigo": antigo, "Palavras do modelo antigo": ", ".join(palavras[(palavras.versao == COMPARA) & (palavras.topico == antigo)]["palavra"].head(6)) + "…",
                   "Mais parecido no modelo novo": f"T{M3.index[j]} {NOMES[M3.index[j]]}", "Cosseno": round(float(cos[i, j]), 2)})
pd.DataFrame(linhas).set_index("Tópico do modelo antigo")
''')
com("c8")

md("""
## 9. E se os aluguéis duvidosos entrassem? (variante `t5i`)
O `aluguel_incerto` são anúncios de aluguel em que o texto **não diz** se a pessoa era escravizada ("precisa-se de uma criada").
Eles ficam fora do modelo principal. Aqui ajustamos o mesmo modelo **com** eles (`t5i`) e comparamos a parcela de cada tema por período.
Os temas recebem o nome pelo mesmo critério de palavras, então a comparação é pelo **nome**, não pelo número.
""")
code('''
VARIANTE = MODELO + "i"
pal_i = ler_tudo(lambda: db.table("topico_palavras").select("versao,topico,palavra,peso").eq("versao", VARIANTE)
                 .order("topico").order("peso", desc=True))
dist_i = ler_tudo(lambda: db.table("anuncio_topicos").select("anuncio_id,topico,proporcao").eq("versao", VARIANTE)
                  .order("anuncio_id").order("topico"))
topo_i = {t: set(g.sort_values("peso", ascending=False)["palavra"].head(12)) for t, g in pal_i.groupby("topico")}
ts_i = sorted(topo_i)
custo_i = [[-len(topo_i[t] & REFERENCIAS[n]) for n in _nomes] for t in ts_i]
nomes_i = {ts_i[i]: (_nomes[j] if -custo_i[i][j] >= 2 else f"Tópico {ts_i[i]} (sem nome)") for i, j in zip(*linear_sum_assignment(custo_i))}
pivo_i = dist_i.pivot(index="anuncio_id", columns="topico", values="proporcao").rename(columns=nomes_i)
com_i = anuncios.drop_duplicates("id").set_index("id")[["periodo_legal"]].join(pivo_i, how="inner")
com_i["periodo"] = pd.Categorical(com_i["periodo_legal"].map(periodo_curto), categories=PERIODOS, ordered=True)
sem = base[list(range(K))].rename(columns=NOMES).assign(periodo=base["periodo"])
media_sem = (sem.groupby("periodo", observed=True).mean() * 100).round(1).reindex(PERIODOS)
media_com = (com_i.groupby("periodo", observed=True)[list(pivo_i.columns)].mean() * 100).round(1).reindex(PERIODOS)
tab = pd.concat({"sem os duvidosos (t5)": media_sem, "com os duvidosos (t5i)": media_com}, axis=1)
print(f"{len(sem)} anúncios sem e {len(com_i)} com os aluguéis duvidosos (proporção média de cada tema por período, %)")
tab.T
''')
com("c8b")

md("""
## 10. O que os resultados dizem e o que não dizem
""")
md(COM.get("c9", "_(a preencher)_"))

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
