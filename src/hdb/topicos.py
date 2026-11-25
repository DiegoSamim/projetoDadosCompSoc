"""Modelagem de tópicos (LDA) sobre o texto padronizado do corpus (hdb.corpus).

As funções de `ajustar` a `anuncios_tipicos` são puras; `processar` lê o corpus do banco e grava o resultado.
"""
from collections import Counter

import numpy as np
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
