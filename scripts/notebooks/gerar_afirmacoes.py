import json
import sys
from pathlib import Path
import nbformat as nbf

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO / "src"))
from hdb import config

SAIDA = RAIZ_REPO / "notebooks" / "afirmacoes.ipynb"
JC = Path(__file__).with_name("comentarios_afirmacoes.json")
COM = json.load(open(JC)) if JC.exists() else {}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t.strip()))
code = lambda t: cells.append(nbf.v4.new_code_cell(t.strip()))
def com(k): md(COM.get(k, "_(comentário a preencher)_"))

md(f"""
# Quadro de afirmações: o que os números sustentam

Este caderno reúne, num quadro só, as conclusões dos cadernos `incerteza` e `robustez_mistura`. Cada linha é uma **afirmação** escrita
antes de olhar o resultado (a lista é fixa, são 9) e recebe um **veredito**.

**Como se decide.** Compara-se o **último período (1871–1888)** com uma **base**: o primeiro período em que há pelo menos 30 anúncios
(e, nas visões ajustadas, 30 anúncios *efetivos*). A base é escolhida por visão; se a da visão bruta e a da visão só JC forem diferentes, o quadro mostra as duas.

| Visão | O que é |
|---|---|
| **Bruta** | todos os anúncios do corpus |
| **Só JC** | só o Jornal do Commercio (sem os bibs `094170_01` e `706744`) |
| **Ajustada** | só para as afirmações 7 a 9: a mistura de tipos (fuga, aluguel, venda, ama de leite) é igualada entre os períodos |

| Veredito | Quer dizer |
|---|---|
| **sustentada** | a tendência bruta passa no teste (p ajustado < 0,05), a diferença último − base tem intervalo de 95% sem zero na bruta e na só JC (e, nos temas, na ajustada), sempre no sentido da frase |
| **parcial** | o sentido é o da frase em todas as visões, mas o intervalo contém zero em alguma (ou o teste de tendência não passa) |
| **não sustentada** | o sentido muda entre as visões, ou contraria a frase, ou o intervalo da visão bruta contém zero, ou a visão ajustada de um tema não confirma |
| **frágil** | mesmo na base alternativa, a base ou o último período têm menos de 30 anúncios em alguma visão |

**Ano da mudança.** Só para as medidas de proporção 1, 2, 3, 5 e 6: ano estimado do degrau na série anual (visão bruta; entre parênteses, só JC); *sem ponto* = não se define (detalhes no caderno `pontos_de_mudanca`). Não altera o veredito, mas, se o ponto some na visão só JC, o motivo avisa "possível efeito de jornal".

**Forma.** *Um degrau* = mais de 60% da mudança total acontece num só passo entre períodos vizinhos; senão, *gradual*.

> **As afirmações 6 a 9 não são achados históricos.** A 6 mede a **mistura da amostra** (quantos anúncios de fuga a busca achou); as 7 a 9 são **temas, que acompanham o tipo do anúncio**.
> Por isso um veredito "sustentada" nelas leva o aviso "(ver natureza)": descreve a amostra, não o que mudou na escravidão.

Corpus `{config.VERSAO_CORPUS}`, campos `{config.VERSAO_CAMPOS}`, temas `{config.VERSAO_TOPICOS}`. Os números dos comentários foram lidos da saída
da própria execução; se o banco mudar, **confira os números de novo**.

> **Cuidado ao ler:** (1) os anúncios vêm de **frases de busca**, não de sorteio; (2) **o bootstrap usa o modelo de temas fixo** e não mede a
> instabilidade do LDA; (3) os anúncios de um período não são independentes (reanúncios, mesmo dono), então **os intervalos são um pouco otimistas**;
> (4) "não sustentada" não prova que nada mudou: pode faltar anúncio.
""")

md("## Preparação: ler o corpus e calcular as medidas")
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
from hdb.afirmacoes import AFIRMACOES, formatar, quadro
from hdb.banco import BancoSupabase
from hdb.medidas import MIN_N, PERIODOS, calcular, carregar
from hdb.pontos_mudanca import calcular_pontos

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 120)
df = carregar(BancoSupabase(), config)
print(f"{len(df)} anúncios no corpus {config.VERSAO_CORPUS} com período legal")
if len(df) != __N_COM__:
    print(f"ATENÇÃO: os comentários deste caderno foram escritos para __N_COM__ anúncios e agora são {len(df)}: "
          "confira os números dos textos antes de usar.")
RESULTADOS = calcular(df)
QUADRO = quadro(RESULTADOS, calcular_pontos(df))
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
''')

md("""
## 1. O quadro
Valores em % (idade em anos). A diferença é último − base, com intervalo de 95% por bootstrap (2.000 repetições, semente fixa).
""")
code('''
display(Markdown(formatar(QUADRO)))
''')
com("c1")

md("""
## 2. Gráficos: valor por período, uma linha por visão
**Círculo aberto** = n (ou n efetivo) menor que 30 naquele período e visão. Cada gráfico traz o veredito.
""")
code('''
CORES = {"bruta": "#0072B2", "jc": "#009E73", "ajustada": "#D55E00"}
ROTULO = {"bruta": "Bruta", "jc": "Só JC", "ajustada": "Ajustada"}
fig, eixos = plt.subplots(3, 3, figsize=(13, 10))
for ax, l in zip(eixos.ravel(), QUADRO):
    r = RESULTADOS[l["id"]]
    ax.set_title(f"{l['id']}. {l['texto']}", fontsize=9, loc="left")
    for k, v in enumerate(["bruta", "jc", "ajustada"]):
        if v not in r:
            continue
        xs = [i + (k - 1) * 0.08 for i, p in enumerate(PERIODOS) if r[v][p]["n"] > 0]
        ys = [r[v][p]["valor"] for p in PERIODOS if r[v][p]["n"] > 0]
        ax.plot(xs, ys, color=CORES[v], lw=1, alpha=0.8, label=ROTULO[v])
        for i, p in enumerate(PERIODOS):
            c = r[v][p]
            if c["n"] > 0:
                ax.plot(i + (k - 1) * 0.08, c["valor"], "o", color=CORES[v], ms=5,
                        mfc="white" if min(c["n"], c["n_ef"]) < MIN_N else CORES[v])
    ax.set_xticks(range(len(PERIODOS)))
    ax.set_xticklabels([p.replace("antes de ", "<") for p in PERIODOS], fontsize=8)
    ax.set_ylabel("anos" if l["id"] == 4 else "%")
    ax.set_xlabel(l["veredito"] + f" · {l['forma']}", fontsize=8)
eixos[0, 0].legend(fontsize=7, frameon=False)
fig.suptitle("Valor por período legal e visão (círculo aberto = n ou n efetivo < 30)")
fig.tight_layout(); plt.show()
''')
com("c2")

md("## 3. O que fica de pé")
md(COM.get("c3", "_(a preencher)_"))

for _c in cells:  # nº de anúncios para o qual os comentários foram escritos (a chave "_n_anuncios" do JSON)
    if _c.cell_type == "code":
        _c.source = _c.source.replace("__N_COM__", str(COM.get("_n_anuncios", 0)))
nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nbf.write(nb, SAIDA)
print("gravado", SAIDA)
