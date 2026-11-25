"""Resumo de uma página do que o banco tem hoje: escreve resumo_dados.md na raiz do projeto.

Uso: python scripts/resumo_dados.py   (só lê o banco; PYTHONPATH=src)

Todos os números vêm do banco; nada é digitado aqui. `ler(banco)` busca os dados e `montar(dados)` escreve o texto
(função pura, testada com dados simulados).
"""
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from hdb import afirmacoes, config, medidas
from hdb.relatorio import num, tabela

SAIDA = RAIZ / "resumo_dados.md"
PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
ANO_INICIO, ANO_FIM = 1821, 1888
SEM_DADOS = "_Sem dados._"

try:  # o nome dos temas passou a morar em hdb.topicos
    from hdb.topicos import nomear
except ImportError:  # TODO: remover esta cópia quando hdb.topicos.nomear existir
    REFERENCIAS = {
        "Fuga: nome, idade e dono": {"anos", "dia", "escravo", "idade", "tiver", "nome", "contra", "souber", "dias", "cor"},
        "Fuga: roupa levada e nação": {"levou", "nacao", "fugiu", "levar", "sera", "corrente", "dia", "preto"},
        "Ama de leite": {"leite", "ama", "meses", "carinhosa", "parto", "criancas", "parda"},
        "Serviço doméstico (aluguel e venda de mulheres)": {"lava", "cozinha", "engoma", "lavar", "engomar", "cozinhar",
                                                            "servico", "aluga", "preta"},
        "Venda de moleques e pretos (lotes)": {"moleque", "pretos", "dois", "vendem", "pagem", "proprio", "cozinheiro"},
        "Venda com preço e qualidades": {"preco", "perfeito", "bonita", "pardo", "forno", "bem", "todo", "servico", "vende"},
    }

    def nomear(palavras_por_topico):
        """{tópico: nome sugerido} pelas palavras de cada tópico (as de maior peso primeiro); sem nome: "Tópico N (sem nome)"."""
        from scipy.optimize import linear_sum_assignment
        topo = {t: set(p[:12]) for t, p in palavras_por_topico.items()}
        ts, nomes = sorted(topo), list(REFERENCIAS)
        custo = [[-len(topo[t] & REFERENCIAS[n]) for n in nomes] for t in ts]
        saida = {t: f"Tópico {t} (sem nome)" for t in ts}
        for i, j in zip(*linear_sum_assignment(custo)):
            if -custo[i][j] >= 2:
                saida[ts[i]] = nomes[j]
        return saida


def periodo_curto(p):
    """'1850–1871 (Eusébio → ...)' vira '1850–1871'."""
    return None if not p else (p if p.startswith("antes") else p.split(" ")[0])


# --- leitura do banco ---

def ler(banco):
    """Lê do banco tudo o que o resumo usa e devolve o dict `dados` (listas e contagens simples)."""
    from hdb.banco import _todas
    cli = banco.cliente
    colunas = "id,periodo_legal,ano,c_tipo,c_sexo,c_idade_min,c_idade_max,c_nacoes,c_recompensa"
    anuncios = _todas(cli.table("anuncios_completos").select(colunas).in_("versao", list(config.VERSOES_ANUNCIOS))
                      .eq("c_versao", config.VERSAO_CAMPOS).order("id"))
    palavras = defaultdict(list)
    for l in _todas(cli.table("topico_palavras").select("topico,palavra,peso").eq("versao", config.VERSAO_TOPICOS)
                    .order("topico").order("peso", desc=True)):
        palavras[l["topico"]].append(l["palavra"])
    mistura = defaultdict(dict)
    for l in _todas(cli.table("anuncio_topicos").select("anuncio_id,topico,proporcao")
                    .eq("versao", config.VERSAO_TOPICOS).order("anuncio_id").order("topico")):
        mistura[l["anuncio_id"]][l["topico"]] = l["proporcao"]
    nomes = {a["bib"]: a["nome"] for a in _todas(cli.table("acervos").select("bib,nome").order("bib"))}
    paginas = Counter()
    for p in _todas(cli.table("paginas").select("id,bib,ano").eq("status", "ok").order("id")):
        if p.get("ano"):
            paginas[(nomes.get(p["bib"]) or p["bib"], p["ano"])] += 1
    quadro = afirmacoes.quadro(medidas.calcular(medidas.carregar(banco, config)))   # ~30 s: bootstrap das 9 medidas
    return {
        "gerado_em": datetime.now().strftime("%Y-%m-%d"),
        "versoes": {"campos": config.VERSAO_CAMPOS, "corpus": config.VERSAO_CORPUS, "topicos": config.VERSAO_TOPICOS},
        "anuncios": anuncios,
        "quadro": quadro,
        "topicos": {"palavras": dict(palavras), "mistura": dict(mistura)},
        "paginas_por_ano": [{"acervo": a, "ano": y, "n": n} for (a, y), n in sorted(paginas.items())],
    }


# --- montagem do texto ---

def _pct(parte, total, casas=0):
    return f"{num(100 * parte / total, casas)}%" if total else "–"


def _intervalos(anos):
    """[1880, 1881, 1882, 1885] -> '1880–1882, 1885'."""
    anos, partes = sorted(set(anos)), []
    i = 0
    while i < len(anos):
        j = i
        while j + 1 < len(anos) and anos[j + 1] == anos[j] + 1:
            j += 1
        partes.append(str(anos[i]) if i == j else f"{anos[i]}–{anos[j]}")
        i = j + 1
    return ", ".join(partes) or "nenhum"


def _por_periodo_e_tipo(anuncios):
    cont = Counter((periodo_curto(a.get("periodo_legal")) or "sem ano", a.get("c_tipo") or "sem tipo") for a in anuncios)
    # "outro" (casas, notícias, mercadorias...) são quase todos os textos e não são anúncios de pessoas: ficam por último
    tipos = sorted({t for _, t in cont}, key=lambda t: (t == "outro", -sum(n for (_, x), n in cont.items() if x == t)))
    periodos = [p for p in PERIODOS + ["sem ano"] if any(p == q for q, _ in cont)]
    linhas = [(p, *[num(cont.get((p, t), 0)) for t in tipos], num(sum(cont.get((p, t), 0) for t in tipos))) for p in periodos]
    if linhas:
        linhas.append(("**Total**", *[num(sum(cont.get((p, t), 0) for p in periodos)) for t in tipos],
                       num(sum(cont.values()))))
    return tabela(("Período", *tipos, "Total"), linhas)


def _temas(dados):
    top = dados.get("topicos") or {}
    palavras, mistura = top.get("palavras") or {}, top.get("mistura") or {}
    if not palavras or not mistura:
        return SEM_DADOS
    nomes = nomear({int(t): p for t, p in palavras.items()})
    topicos = sorted(nomes)
    por_periodo = defaultdict(list)
    for a in dados.get("anuncios") or []:
        m = mistura.get(a["id"]) or mistura.get(str(a["id"]))
        if m and periodo_curto(a.get("periodo_legal")) in PERIODOS:
            por_periodo[periodo_curto(a["periodo_legal"])].append({int(k): v for k, v in m.items()})
    periodos = [p for p in PERIODOS if por_periodo.get(p)]
    linhas = []
    for t in topicos:
        celulas = [f"{num(100 * sum(m.get(t, 0) for m in por_periodo[p]) / len(por_periodo[p]), 1)}%" for p in periodos]
        linhas.append((f"T{t}", nomes[t], ", ".join(palavras.get(t, palavras.get(str(t), []))[:5]), *celulas))
    cab = ("Tema", "Nome sugerido", "Palavras principais", *[f"{p} (n = {num(len(por_periodo[p]))})" for p in periodos])
    return (tabela(cab, linhas) + "\n\n> **Ressalva:** os temas acompanham o tipo do anúncio (fuga, venda, aluguel, ama de leite): "
            "onde há mais anúncios de um tipo, o tema desse tipo pesa mais. Quando a mistura de tipos é igualada entre os períodos, "
            "os temas **não mostram mudança** (veja o caderno `robustez_mistura`); por isso esta tabela descreve a amostra e "
            "**não deve ser lida como uma tendência histórica**. Os nomes são sugestões, o grupo ainda os confirma.")


def _quadro(dados):
    q = dados.get("quadro")
    if not q:
        return SEM_DADOS
    return ("Nove afirmações fixadas antes de olhar os resultados. Cada uma compara o último período (1871–1888) com a base "
            "(o primeiro período com 30 anúncios ou mais), na visão bruta e só no Jornal do Commercio (e, nos temas, com a "
            "mistura de tipos igualada). **Sustentada** = a mudança é real em todas as visões; **parcial** = mesmo sentido, mas "
            "o intervalo inclui zero em alguma; **não sustentada** = o sentido muda ou contraria a frase; **frágil** = poucos "
            "anúncios. As afirmações 6 a 9 descrevem a amostra (mistura de tipos e temas), não achados históricos. "
            "Detalhes no caderno `afirmacoes`.\n\n" + afirmacoes.formatar(q)
            + "\n\n**Ressalva de leitura (caderno `validacao_campos`).** Os campos são extraídos do texto por regras, e o código "
            "perde parte deles. Conferido à mão em 20 fugas por período: a **nação citada** e as **marcas no corpo** caem de "
            "fato; a **queda da recompensa** que o código mostra é **maior que a real** (o código perde mais recompensas nos "
            "períodos recentes), e a **alta da idade citada** vem em boa parte de o código achar poucas idades nos anúncios mais "
            "antigos. A afirmação 1 deve ser tratada como possível, não como medida; a 4, como frágil.")


def _sinais(anuncios):
    partes = []
    # fuga com recompensa por período
    fugas = defaultdict(lambda: [0, 0])
    for a in anuncios:
        p = periodo_curto(a.get("periodo_legal"))
        if a.get("c_tipo") == "fuga" and p in PERIODOS:
            fugas[p][0] += 1
            fugas[p][1] += bool(a.get("c_recompensa"))
    linhas = [(p, num(fugas[p][0]), _pct(fugas[p][1], fugas[p][0])) for p in PERIODOS if fugas[p][0]]
    partes.append("**Fuga com recompensa, por período.** " + ("O anúncio oferece recompensa (gratificação, alviçaras)?\n\n"
                  + tabela(("Período", "Anúncios de fuga", "Com recompensa"), linhas)
                  + "\n\n_Ressalva: períodos com poucos anúncios variam muito; a amostra vem de frases de busca._"
                  if linhas else SEM_DADOS))
    # sexo por tipo
    sexo = defaultdict(Counter)
    for a in anuncios:
        if a.get("c_tipo") not in (None, "outro"):
            sexo[a["c_tipo"]][a.get("c_sexo") or "?"] += 1
    linhas = [(t, num(sum(c.values())), _pct(c["f"], c["f"] + c["m"]), _pct(c["m"], c["f"] + c["m"]), _pct(c["?"], sum(c.values())))
              for t, c in sorted(sexo.items(), key=lambda x: -sum(x[1].values()))]
    partes.append("**Sexo, por tipo.** Feminino e masculino são % dos anúncios em que o sexo aparece.\n\n"
                  + (tabela(("Tipo", "Anúncios", "Feminino", "Masculino", "Sexo não aparece"), linhas) if linhas else SEM_DADOS)
                  + "\n\n_Ressalva: o sexo vem de palavras do texto; \"ama de leite\" é feminino por construção._")
    # nação por período
    nacoes = defaultdict(Counter)
    com_nacao = Counter()
    for a in anuncios:
        p = periodo_curto(a.get("periodo_legal"))
        if p in PERIODOS and a.get("c_nacoes") and a.get("c_tipo") not in (None, "outro"):
            com_nacao[p] += 1
            nacoes[p].update(set(a["c_nacoes"]))
    linhas = [(p, num(com_nacao[p]), ", ".join(f"{n} ({_pct(c, com_nacao[p])})" for n, c in nacoes[p].most_common(3)))
              for p in PERIODOS if com_nacao[p]]
    partes.append("**Nação, por período.** As 3 mais citadas entre os anúncios que citam alguma nação.\n\n"
                  + (tabela(("Período", "Anúncios com nação", "Mais citadas"), linhas) if linhas else SEM_DADOS)
                  + "\n\n_Ressalva: nação é o que o anunciante escreveu; muda de uso ao longo do século._")
    # idade
    idades = defaultdict(list)
    for a in anuncios:
        if a.get("c_idade_min") is not None and a.get("c_tipo") not in (None, "outro"):
            idades[a["c_tipo"]].append(a["c_idade_min"])
    linhas = [(t, num(len(v)), num(statistics.median(v), 1)) for t, v in sorted(idades.items(), key=lambda x: -len(x[1]))]
    partes.append("**Idade, por tipo.** Só dos anúncios que dizem a idade.\n\n"
                  + (tabela(("Tipo", "Com idade", "Idade mediana (anos)"), linhas) if linhas else SEM_DADOS)
                  + "\n\n_Ressalva: a idade é a que o anunciante disse (em geral aproximada)._")
    return "\n\n".join(partes)


def _cobertura(paginas):
    if not paginas:
        return SEM_DADOS
    por_jornal = defaultdict(lambda: defaultdict(Counter))  # jornal -> década -> ano -> páginas
    todos = set()
    for p in paginas:
        por_jornal[p["acervo"]][p["ano"] // 10 * 10][p["ano"]] += p["n"]
        todos.add(p["ano"])
    linhas = []
    for jornal in sorted(por_jornal):
        for dec in sorted(por_jornal[jornal]):
            anos = por_jornal[jornal][dec]
            linhas.append((jornal, f"{dec}s", num(sum(anos.values())), f"{len(anos)} de 10: {_intervalos(anos)}"))
    sem = [a for a in range(ANO_INICIO, ANO_FIM + 1) if a not in todos]
    destaque = [f"**{a}**" if a in (1887, 1888) else str(a) for a in sem]
    aviso = (f"**Anos sem nenhuma página lida ({ANO_INICIO}–{ANO_FIM}), {num(len(sem))} de {num(ANO_FIM - ANO_INICIO + 1)}:** "
             + (", ".join(destaque) if sem else "nenhum") + ".")
    return tabela(("Jornal", "Década", "Páginas lidas", "Anos presentes"), linhas) + "\n\n" + aviso


LIMITES = (
    "**Amostra por busca.** Os anúncios vêm de páginas achadas por frases de busca, não de sorteio: as proporções "
    "(tipo, sexo) descrevem o que a busca encontrou, não o jornal inteiro.",
    "**Períodos desiguais.** Cada período tem outro número de anúncios, e antes de 1831 a amostra vem de outros jornais; "
    "parte da diferença entre períodos pode ser diferença de jornal ou de anos cobertos (ver o mapa de cobertura).",
    "**Tópicos moderadamente estáveis.** Mudar a semente do sorteio ou alguns anúncios reorganiza os tópicos; "
    "os temas são pistas, e os nomes são hipóteses do grupo.",
)


def montar(dados):
    """O resumo em Markdown (uma página) a partir do dict de `ler`."""
    v = dados.get("versoes") or {}
    anuncios = dados.get("anuncios") or []
    secoes = [
        "# Resumo dos dados",
        f"Gerado em {dados.get('gerado_em') or '–'} a partir do banco. Versões: campos `{v.get('campos', '–')}`, "
        f"corpus `{v.get('corpus', '–')}`, tópicos `{v.get('topicos', '–')}`. Todos os números são lidos do banco.",
        f"## Anúncios por período e tipo\n\n{num(len(anuncios))} textos separados nas páginas, dos quais "
        f"{num(sum(1 for a in anuncios if a.get('c_tipo') not in (None, 'outro')))} são anúncios de pessoas "
        f"(os demais, tipo `outro`, são casas, notícias, mercadorias etc.).\n\n" + (_por_periodo_e_tipo(anuncios) if anuncios else SEM_DADOS),
        "## Os temas e o peso de cada um por período\n\nProporção média do tema nos anúncios de cada período.\n\n" + _temas(dados),
        "## Quadro de afirmações\n\n" + _quadro(dados),
        "## Sinais principais\n\n" + _sinais(anuncios),
        "## Cobertura: onde temos páginas\n\n" + _cobertura(dados.get("paginas_por_ano") or []),
        "## Os 3 limites principais\n\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(LIMITES, 1)),
    ]
    return "\n\n".join(secoes) + "\n"


def main():
    from hdb.banco import BancoSupabase
    texto = montar(ler(BancoSupabase()))
    SAIDA.write_text(texto, encoding="utf-8")
    print("gravado", SAIDA)


if __name__ == "__main__":
    main()
