"""Modelagem de tópicos (LDA) sobre o texto padronizado do corpus (hdb.corpus).

As funções de `ajustar` a `anuncios_tipicos` são puras; `processar` lê o corpus do banco e grava o resultado.
"""
import random
from collections import Counter

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

from hdb import config


def ajustar(textos, n_topicos, semente):
    """Ajusta o LDA. Devolve (modelo, vetorizador, matriz de contagens documento x palavra)."""
    vetorizador = CountVectorizer(min_df=config.TOPICOS_MIN_DF, max_df=config.TOPICOS_MAX_DF)
    matriz = vetorizador.fit_transform(textos)
    modelo = LatentDirichletAllocation(n_components=n_topicos, random_state=semente, learning_method="batch")
    modelo.fit(matriz)
    return modelo, vetorizador, matriz


# Nomes SUGERIDOS (hipóteses do grupo, não fatos). O LDA numera os tópicos ao acaso (a cada rodada o T0 pode ser
# outro), então cada nome vem das palavras de referência: o tópico recebe o nome cujas palavras mais aparecem entre
# as suas 12 de maior peso.
REFERENCIAS = {
    "Fuga: nome, idade e dono": {"anos", "dia", "escravo", "idade", "tiver", "nome", "contra", "souber", "dias", "cor"},
    "Fuga: roupa levada e nação": {"levou", "nacao", "fugiu", "levar", "sera", "corrente", "dia", "preto"},
    "Ama de leite": {"leite", "ama", "meses", "carinhosa", "parto", "criancas", "parda"},
    "Serviço doméstico (aluguel)": {"aluga", "lava", "cozinha", "engoma", "servico", "todo", "faz", "precisa"},
    "Venda de mulheres (lavar, engomar, cozinhar)": {"vende", "lavar", "engomar", "cozinhar", "sabe", "idade", "anos", "preta", "bonita"},
    "Venda de moleques e pretos (lotes)": {"moleque", "pretos", "dois", "vendem", "escravos", "qualquer", "sendo", "idade"},
    "Venda com preço e qualidades": {"preco", "perfeito", "bonita", "pardo", "forno", "bem", "todo", "servico", "vende"},
}
MIN_EM_COMUM = 1.5  # pontuação mínima (palavras em comum, ponderadas pela raridade) para um tópico receber o nome


def nomear(palavras_por_topico, referencias=REFERENCIAS):
    """{tópico: nome}. Entrada: {tópico: iterável das palavras de maior peso}.

    Atribuição ótima sem repetir nome (`linear_sum_assignment`). A pontuação de um tópico para um nome soma, para cada
    palavra em comum, `1 / (nº de nomes cuja referência tem essa palavra)`: "leite" e "ama" (só de ama de leite)
    valem mais que "servico" e "todo" (de vários nomes). O tópico cujo melhor nome pontua menos de `MIN_EM_COMUM`
    (ou que fica sem nome por haver mais tópicos que nomes) vira "Tópico N (sem nome)".
    """
    topicos = sorted(palavras_por_topico)
    nomes = list(referencias)
    conjuntos = {t: set(palavras_por_topico[t]) for t in topicos}
    saida = {t: f"Tópico {t} (sem nome)" for t in topicos}
    if not topicos or not nomes:
        return saida
    em_quantos = {}
    for n in nomes:
        for palavra in referencias[n]:
            em_quantos[palavra] = em_quantos.get(palavra, 0) + 1
    custo = [[-sum(1 / em_quantos[w] for w in conjuntos[t] & set(referencias[n])) for n in nomes] for t in topicos]
    for i, j in zip(*linear_sum_assignment(custo)):
        if -custo[i][j] >= MIN_EM_COMUM:
            saida[topicos[i]] = nomes[j]
    return saida


def equilibrado(textos_por_periodo, n, sorteios=10, n_topicos=6, referencias=REFERENCIAS):
    """Modelo de tópicos com o MESMO nº de anúncios por período (para os períodos não pesarem diferente).

    `textos_por_periodo = {periodo: [texto_padrao, ...]}`. No sorteio `i` (semente `i`) sorteia `min(n, len(lista))`
    textos de cada período (quem tem menos de `n` entra inteiro), ajusta o LDA sobre o conjunto, nomeia os tópicos
    (`nomear`) e tira a proporção média de cada tema por período. Devolve:
      "sorteios": [{nome: {periodo: proporção média}}], um por sorteio (temas sem nome somados em "(sem nome)");
      "media", "minimo", "maximo": {nome: {periodo: valor}} entre os sorteios (só os sorteios em que o nome apareceu;
                                   "(sem nome)" fica de fora);
      "n_usado": {periodo: n sorteado}; "curtos": períodos com menos de `n` (entraram inteiros);
      "sem_nome": total de tópicos sem nome em todos os sorteios; "sem_nome_por_sorteio": lista.
    """
    periodos = list(textos_por_periodo)
    n_usado = {p: min(n, len(textos_por_periodo[p])) for p in periodos}
    curtos = [p for p in periodos if len(textos_por_periodo[p]) < n]
    resultados, sem_nome = [], []
    for i in range(sorteios):
        rng = random.Random(i)
        textos, rotulos = [], []
        for p in periodos:
            for t in rng.sample(list(textos_por_periodo[p]), n_usado[p]):
                textos.append(t)
                rotulos.append(p)
        modelo, vetorizador, matriz = ajustar(textos, n_topicos, i)
        palavras = palavras_dos_topicos(modelo, vetorizador.get_feature_names_out())
        nomes = nomear({t: [w for w, _ in lista] for t, lista in enumerate(palavras)}, referencias)
        mist = misturas(modelo, matriz)
        rotulos = np.array(rotulos)
        res = {}
        for t, nome in enumerate(nomes[k] for k in range(n_topicos)):
            if nome.endswith("(sem nome)"):
                nome = "(sem nome)"
            linha = res.setdefault(nome, {p: 0.0 for p in periodos})
            for p in periodos:
                if n_usado[p]:
                    linha[p] += float(mist[rotulos == p, t].mean())
        resultados.append(res)
        sem_nome.append(sum(1 for v in nomes.values() if v.endswith("(sem nome)")))
    todos = sorted({nome for r in resultados for nome in r if nome != "(sem nome)"})
    media, minimo, maximo = {}, {}, {}
    for nome in todos:
        for p in periodos:
            vals = [r[nome][p] for r in resultados if nome in r]
            media.setdefault(nome, {})[p] = float(np.mean(vals))
            minimo.setdefault(nome, {})[p] = float(min(vals))
            maximo.setdefault(nome, {})[p] = float(max(vals))
    return {"sorteios": resultados, "media": media, "minimo": minimo, "maximo": maximo, "n_usado": n_usado,
            "curtos": curtos, "sem_nome": sum(sem_nome), "sem_nome_por_sorteio": sem_nome}


def semente_representativa(textos, n_topicos, sementes=range(10)):
    """A semente cujo modelo mais se parece com os das outras: (semente, {semente: similaridade média com as demais}).

    O LDA depende da semente (3 anúncios a mais já reorganizaram os 6 tópicos de uma semente fixa). Em vez de apostar
    na semente 0, ajusta uma vez por semente e fica com a mais "central": para cada par de modelos, cada tópico se
    casa com o tópico mais parecido do outro (cosseno entre as distribuições de palavras) e se tira a média.
    """
    topicos = {}
    for semente in sementes:
        modelo, _, _ = ajustar(textos, n_topicos, semente)
        pesos = modelo.components_ / modelo.components_.sum(axis=1, keepdims=True)
        topicos[semente] = pesos / np.linalg.norm(pesos, axis=1, keepdims=True)
    medias = {}
    for a, ta in topicos.items():
        outras = [float((ta @ tb.T).max(axis=1).mean()) for b, tb in topicos.items() if b != a]
        medias[a] = sum(outras) / len(outras) if outras else 1.0
    return max(medias, key=lambda a: (medias[a], -a)), medias


def palavras_dos_topicos(modelo, vocabulario, n=config.TOPICOS_PALAVRAS):
    """Por tópico, as `n` palavras mais fortes como [(palavra, peso normalizado)] (pesos somam 1 no tópico inteiro)."""
    pesos = modelo.components_ / modelo.components_.sum(axis=1, keepdims=True)
    return [[(str(vocabulario[j]), float(linha[j])) for j in np.argsort(-linha, kind="stable")[:n]] for linha in pesos]


def misturas(modelo, matriz):
    """Por documento, o vetor de proporções dos tópicos (soma 1)."""
    return modelo.transform(matriz)


def anuncios_tipicos(mist, ids, n=config.TOPICOS_TIPICOS):
    """Por tópico, os ids dos `n` anúncios com maior proporção nele."""
    mist = np.asarray(mist)
    return [[ids[i] for i in np.argsort(-mist[:, t], kind="stable")[:n]] for t in range(mist.shape[1])]


def dominantes(mist):
    """O tópico de maior proporção de cada documento."""
    return [int(t) for t in np.argmax(mist, axis=1)]


def linhas_palavras(palavras):
    """Linhas de `topico_palavras`."""
    return [{"topico": t, "palavra": p, "peso": w} for t, lista in enumerate(palavras) for p, w in lista]


def linhas_misturas(ids, mist):
    """Linhas de `anuncio_topicos`: uma por anúncio e tópico."""
    return [{"anuncio_id": i, "topico": t, "proporcao": float(p)}
            for i, linha in zip(ids, mist) for t, p in enumerate(linha)]


def resumir(anuncios, mist, palavras, tipicos, perplexidade):
    """Por tópico: palavras, nº de anúncios dominantes, distribuição por período legal e tipo, anúncios típicos."""
    topicos = [{"topico": t, "palavras": palavras[t], "n": 0, "por_periodo": Counter(), "por_tipo": Counter(),
                "tipicos": tipicos[t]} for t in range(len(palavras))]
    for a, t in zip(anuncios, dominantes(mist)):
        topicos[t]["n"] += 1
        topicos[t]["por_periodo"][a.get("periodo_legal") or "sem ano"] += 1
        topicos[t]["por_tipo"][a.get("c_tipo") or "sem tipo"] += 1
    return {"n_docs": len(anuncios), "perplexidade": perplexidade, "topicos": topicos}


def formatar_resumo(r):
    """O resumo de `resumir` em texto para o terminal."""
    def grupo(c):
        return ", ".join(f"{k}: {v}" for k, v in sorted(c.items())) or "nenhum"
    linhas = [f"{r['n_docs']} anúncios, {len(r['topicos'])} tópicos, perplexidade {r['perplexidade']:.1f}"]
    for t in r["topicos"]:
        linhas += [f"Tópico {t['topico']}: {t['n']} anúncios", "  " + ", ".join(p for p, _ in t["palavras"]),
                   f"  por período: {grupo(t['por_periodo'])}", f"  por tipo: {grupo(t['por_tipo'])}",
                   "  típicos (id): " + (", ".join(map(str, t["tipicos"])) or "nenhum")]
    return "\n".join(linhas)


def processar(banco, versao_corpus=config.VERSAO_CORPUS, n_topicos=config.N_TOPICOS, semente=config.SEMENTE_TOPICOS,
              versao=config.VERSAO_TOPICOS):
    """Ajusta o LDA sobre o corpus e grava (regravar a mesma `versao` substitui). Devolve o resumo.

    `semente` pode ser "auto": usa a semente mais representativa de 10 (`semente_representativa`).
    """
    anuncios = [a for a in banco.anuncios_do_corpus(versao_corpus) if (a.get("texto_padrao") or "").strip()]
    if not anuncios:
        raise ValueError(f"corpus {versao_corpus!r} vazio: rode `hdb corpus` antes")
    textos = [a["texto_padrao"] for a in anuncios]
    if semente == "auto":  # a mais representativa entre 10 sementes (ver `semente_representativa`)
        semente, _ = semente_representativa(textos, n_topicos)
    modelo, vetorizador, matriz = ajustar(textos, n_topicos, semente)
    vocabulario = vetorizador.get_feature_names_out()
    palavras = palavras_dos_topicos(modelo, vocabulario)
    mist = misturas(modelo, matriz)
    ids = [a["id"] for a in anuncios]
    perplexidade = float(modelo.perplexity(matriz))
    cabecalho = {"versao": versao, "versao_corpus": versao_corpus, "n_topicos": n_topicos, "semente": semente,
                 "n_docs": len(ids), "n_vocab": len(vocabulario), "perplexidade": perplexidade}
    banco.registrar_topicos(cabecalho, linhas_palavras(palavras), linhas_misturas(ids, mist))
    return resumir(anuncios, mist, palavras, anuncios_tipicos(mist, ids), perplexidade)
