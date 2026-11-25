import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "material_do_grupo.ipynb"
JC = Path(__file__).with_name("comentarios_material.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Material para as decisões do grupo

Campos `{config.VERSAO_CAMPOS}`, corpus `{config.VERSAO_CORPUS}`, tópicos `{config.VERSAO_TOPICOS}`. Quatro partes:
(a) aluguéis duvidosos, (b) os temas e seus nomes, (c) trocas de OCR da limpeza, (d) conferência de uma amostra.
""")
com("intro")

md("## Preparação: ler o banco\nO banco devolve no máximo 1000 linhas por consulta, então lemos em blocos (paginação). Este caderno **só lê**: não grava nada no banco nem em arquivos.")
code('''
import sys
from pathlib import Path

RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

import json, random
from IPython.display import HTML, display
import pandas as pd
from hdb import config, corpus
from hdb.banco import BancoSupabase
from resumo_dados import nomear   # nomes sugeridos dos temas (usa hdb.topicos.nomear quando existir)

pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 220)
banco = BancoSupabase()
db = banco.cliente

def ler_tudo(consulta, bloco=1000):
    """Executa a consulta em blocos de 1000 linhas e junta o resultado."""
    linhas, inicio = [], 0
    while True:
        parte = consulta().range(inicio, inicio + bloco - 1).execute().data
        linhas += parte
        if len(parte) < bloco:
            return pd.DataFrame(linhas)
        inicio += bloco

def periodo_curto(p):
    return "sem ano" if not isinstance(p, str) else (p if p.startswith("antes") else p.split(" ")[0])
PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888", "sem ano"]

def trecho(texto, n):
    t = " ".join(str(texto).split())
    return t if len(t) <= n else t[:n].rstrip() + "…"

def mostrar(tabela, vazio):
    """Mostra a tabela e o n; se não há linhas, escreve a frase em vez de falhar."""
    if len(tabela) == 0:
        print(vazio)
        return
    print(f"n = {len(tabela)}")
    html = tabela.reset_index(drop=True).to_html(index=False, escape=True).replace("\\n", "<br>")
    display(HTML("<style>.material td, .material th {text-align: left; vertical-align: top;}</style>"
                 + html.replace('class="dataframe"', 'class="dataframe material"')))
''')

# (a)
md("""
## Parte A. Aluguéis duvidosos
Anúncios de aluguel (`aluguel_incerto`) em que o texto não diz que a pessoa é escravizada.
""")
code('''
inc = ler_tudo(lambda: db.table("anuncios_completos").select("id,periodo_legal,texto,c_evidencias")
               .in_("versao", list(config.VERSOES_ANUNCIOS)).eq("c_versao", config.VERSAO_CAMPOS)
               .eq("c_tipo", "aluguel_incerto").order("id"))
if len(inc) == 0:
    print("Não há anúncios de aluguel duvidoso nesta versão de campos.")
else:
    inc["periodo"] = pd.Categorical(inc["periodo_legal"].map(periodo_curto), categories=PERIODOS, ordered=True)
    print(f"{len(inc)} anúncios de aluguel duvidoso (campos {config.VERSAO_CAMPOS}).")
    if len(inc) != __N_COM__:
        print(f"ATENÇÃO: os comentários deste caderno foram escritos para __N_COM__ anúncios e agora são {len(inc)}: "
              "confira os números dos textos antes de usar.")
    por_periodo = inc.groupby("periodo", observed=True).size().rename("Anúncios").to_frame()
    por_periodo.index.name = "Período"
    print("\\nPor período legal (n por linha):")
    display(por_periodo)
''')
code('''
def motivo(ev):
    if isinstance(ev, str):
        try:
            ev = json.loads(ev)
        except ValueError:
            return ev
    return (ev or {}).get("tipo", "(sem motivo registrado)")

if len(inc):
    amostra = inc.sample(min(20, len(inc)), random_state=42).sort_values("id")
    ex = pd.DataFrame({"id": amostra["id"], "Período": amostra["periodo"].astype(str),
                       "Texto (até 220 caracteres)": amostra["texto"].map(lambda t: trecho(t, 220)),
                       "Motivo (evidência do campo)": amostra["c_evidencias"].map(motivo)})
    print("20 exemplos sorteados (semente 42):")
    mostrar(ex, "Sem exemplos.")
''')
com("a")

# (b)
md("""
## Parte B. Os temas
Para o modelo de tópicos da versão `""" + config.VERSAO_TOPICOS + """`: nome sugerido, as 12 palavras de maior peso, quantos anúncios
têm aquele tema como o mais forte (n), de que tipos são e 5 anúncios típicos (os de maior proporção do tema).
""")
code('''
MODELO = config.VERSAO_TOPICOS
pal = ler_tudo(lambda: db.table("topico_palavras").select("topico,palavra,peso").eq("versao", MODELO)
               .order("topico").order("peso", desc=True))
dist = ler_tudo(lambda: db.table("anuncio_topicos").select("anuncio_id,topico,proporcao").eq("versao", MODELO)
                .order("anuncio_id").order("topico"))
if len(pal) == 0 or len(dist) == 0:
    print(f"O modelo {MODELO} não tem dados no banco.")
else:
    ids = sorted(dist["anuncio_id"].unique())
    anu = ler_tudo(lambda: db.table("anuncios_completos").select("id,periodo_legal,c_tipo,texto")
                   .in_("versao", list(config.VERSOES_ANUNCIOS)).eq("c_versao", config.VERSAO_CAMPOS).order("id"))
    anu = anu[anu["id"].isin(ids)].drop_duplicates("id").set_index("id")
    palavras = {int(t): list(g["palavra"]) for t, g in pal.groupby("topico")}
    NOMES = nomear(palavras)
    pivo = dist.pivot(index="anuncio_id", columns="topico", values="proporcao").fillna(0)
    base = anu.join(pivo, how="inner")
    base["dominante"] = base[list(pivo.columns)].idxmax(axis=1)
    linhas = []
    for t in sorted(palavras):
        do_tema = base[base["dominante"] == t]
        tipos = do_tema["c_tipo"].value_counts(normalize=True)
        dist_tipo = ", ".join(f"{k} {100 * v:.0f}%" for k, v in tipos.items()) or "–"
        tip = base.sort_values(t, ascending=False).head(config.TOPICOS_TIPICOS)
        tipicos = "\\n".join(f"• [id {i}, {r['c_tipo']}, {r[t]:.2f}] {trecho(r['texto'], 300)}" for i, r in tip.iterrows())
        linhas.append({"Tópico": f"T{t}", "Nome sugerido": NOMES[t], "12 palavras": ", ".join(palavras[t][:12]),
                       "n": len(do_tema), "Tipos (% dos anúncios do tema)": dist_tipo,
                       f"{config.TOPICOS_TIPICOS} anúncios típicos (300 caracteres)": tipicos,
                       "Nome escolhido pelo grupo": ""})
    print(f"{len(base)} anúncios no modelo {MODELO}; n = anúncios cujo tema mais forte é aquele.")
    mostrar(pd.DataFrame(linhas), "Sem temas.")
''')
com("b")

# (c)
md("""
## Parte C. Trocas de OCR da limpeza
A limpeza descobre erros de OCR (palavra rara a uma letra de uma palavra muito mais frequente). Aqui repetimos a
descoberta sobre os anúncios selecionados do corpus, como em `corpus.processar`, **sem gravar nada**.
""")
code('''
todos = banco.anuncios_para_corpus(config.VERSAO_CAMPOS)
sel = [a for a in todos if corpus.selecionar(a)]
if not sel:
    print("Nenhum anúncio selecionado para o corpus.")
else:
    padrao = [corpus.padronizar(a["texto"]) for a in sel]
    desc = corpus.descobrir_ocr(padrao)
    freq = {}
    for t in padrao:
        for p in set(t.split()):
            freq[p] = freq.get(p, 0) + 1
    print(f"{len(sel)} anúncios selecionados; {len(desc['aplicadas'])} trocas aplicadas, {len(desc['recusadas'])} recusadas.")
    ap = pd.DataFrame([{"Erro": w, "Correta": v, "Anúncios com o erro": freq.get(w, 0),
                        "Anúncios com a correta": freq.get(v, 0), "Aprovada? (s/n)": ""}
                       for w, v in desc["aplicadas"].items()]).sort_values("Anúncios com o erro", ascending=False) \\
        if desc["aplicadas"] else pd.DataFrame()
    print("\\nTrocas aplicadas:")
    mostrar(ap, "Nenhuma troca foi aplicada.")
    rec = pd.DataFrame([{"Palavra": w, "Candidata": v, "Anúncios com a palavra": n_w, "Anúncios com a candidata": n_v,
                         "Por que foi recusada": m} for w, v, n_w, n_v, m in desc["recusadas"]])
    if len(rec):
        rec = rec.sort_values("Anúncios com a palavra", ascending=False).head(10)
    print("\\nAs 10 recusadas mais frequentes:")
    mostrar(rec, "Nenhuma troca foi recusada.")
''')
com("c")

# (d)
md("""
## Parte D. Conferência de uma amostra
**Os rótulos "Claude" são de Claude, não de pessoas.** O grupo preenche as duas últimas colunas.
""")
code('''
FIX = RAIZ / "tests" / "fixtures"
def carregar(nome, n=None):
    arq = FIX / nome
    if not arq.exists():
        return []
    itens = json.load(open(arq, encoding="utf-8"))
    return random.Random(42).sample(itens, min(n, len(itens))) if n else itens

def tabela_conferencia(itens):
    return pd.DataFrame([{"id": i["id"], "Período": i.get("periodo"), "Texto (até 300 caracteres)": trecho(i["texto"], 300),
                          "Tipo do código antigo (c4)": i.get("tipo_c4"), "Tipo certo (Claude)": i.get("tipo_certo"),
                          "É anúncio? (Claude)": "sim" if i.get("e_anuncio") else "não",
                          "Tipo certo segundo o grupo": "", "É anúncio de pessoa escravizada? s/n": ""} for i in itens])

print("D1. Os 40 anúncios de conferencia_extra.json")
mostrar(tabela_conferencia(carregar("conferencia_extra.json")), "Arquivo conferencia_extra.json ausente ou vazio.")
''')
code('''
print("D2. 60 anúncios de conferencia.json (sorteados, semente 42)")
mostrar(tabela_conferencia(carregar("conferencia.json", 60)), "Arquivo conferencia.json ausente ou vazio.")
''')
com("d")

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
