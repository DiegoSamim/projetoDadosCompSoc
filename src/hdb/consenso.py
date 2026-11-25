"""Consenso entre sementes do LDA: os temas se repetem quando só a semente muda?

Treina o LDA com várias sementes (mesmo corpus e hiperparâmetros de `hdb topicos`), emparelha cada rodada com a
rodada de referência pelo método húngaro sobre a distância de Jensen–Shannon entre distribuições tópico-palavra e mede
(a) a estabilidade de cada tema da referência e (b) quanto a parcela do tema por período varia entre as sementes.
Tudo em memória: nada é gravado no banco. As funções de `emparelhar` a `resumir_parcelas` são puras.
"""
import random

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.special import rel_entr

from hdb import topicos as T

SEMENTE_BASE = 20251125  # as sementes das rodadas saem dela (fixas, reproduzíveis)
N_SEMENTES = 30
MIN_ESTAVEL = 0.70  # tema com estabilidade abaixo disso é "instável"


def sementes_fixas(n=N_SEMENTES, base=SEMENTE_BASE):
    """`n` sementes distintas derivadas de `base`."""
    return random.Random(base).sample(range(1, 1_000_000), n)


def periodo_curto(p):
    """"1831–1850 (Feijó → Eusébio)" vira "1831–1850"; "antes de 1831" fica como está."""
    return p if p.startswith("antes") else p.split(" ")[0]


def distancias(a, b):
    """Matriz de Jensen–Shannon (base 2, entre 0 e 1) entre as linhas de `a` e as de `b` (distribuições)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = (a[:, None, :] + b[None, :, :]) / 2
    js = (rel_entr(a[:, None, :], m).sum(-1) + rel_entr(b[None, :, :], m).sum(-1)) / 2 / np.log(2)
    return np.sqrt(np.clip(js, 0, 1))


def limiar_de(pesos_ref):
    """Limiar de "mesmo tema": metade da mediana das distâncias entre temas DISTINTOS da referência.

    Se uma rodada reproduz um tema a menos da metade da distância típica entre dois temas diferentes, ele está
    mais perto do tema da referência do que de qualquer outro e não pode ser confundido com outro tema.
    """
    d = distancias(pesos_ref, pesos_ref)
    return float(np.median(d[np.triu_indices(len(d), k=1)]) / 2)


def emparelhar(pesos_ref, pesos):
    """Casa cada tema da referência com um tema da rodada (húngaro, sem repetir).

    Devolve (perm, dist): `perm[i]` é o tópico da rodada emparelhado ao tema `i` da referência e `dist[i]` a distância.
    """
    d = distancias(pesos_ref, pesos)
    linhas, colunas = linear_sum_assignment(d)
    return colunas[np.argsort(linhas)], d[linhas, colunas][np.argsort(linhas)]


def parcelas_por_periodo(mist, periodos, ordem):
    """{periodo: vetor da parcela média de cada tópico}, só para os períodos de `ordem`."""
    mist, periodos = np.asarray(mist), np.asarray(periodos)
    return {p: mist[periodos == p].mean(axis=0) for p in ordem if (periodos == p).any()}


def treinar(textos, periodos, n_topicos, semente, ordem):
    """Uma rodada: {"pesos": tópico x palavra (linhas somam 1), "parcelas": {periodo: vetor}, "palavras": [[palavra]]}."""
    modelo, vetorizador, matriz = T.ajustar(textos, n_topicos, semente)
    pesos = modelo.components_ / modelo.components_.sum(axis=1, keepdims=True)
    palavras = [[p for p, _ in lista] for lista in T.palavras_dos_topicos(modelo, vetorizador.get_feature_names_out())]
    return {"pesos": pesos, "parcelas": parcelas_por_periodo(T.misturas(modelo, matriz), periodos, ordem),
            "palavras": palavras}


def resumir_parcelas(valores):
    """Mediana e intervalo de 2,5–97,5% de uma lista de parcelas (uma por semente)."""
    return {"mediana": float(np.median(valores)), "p2_5": float(np.percentile(valores, 2.5)),
            "p97_5": float(np.percentile(valores, 97.5))}


def resumir(ref, rodadas, nomes=None, limiar=None, min_estavel=MIN_ESTAVEL):
    """Consenso de `rodadas` (lista de saídas de `treinar`) em relação a `ref` (também saída de `treinar`).

    Por tema da referência: distâncias ao tema emparelhado em cada rodada, estabilidade (fração das rodadas com
    distância <= limiar), `instavel` (estabilidade < `min_estavel`) e, por período, a parcela do tema emparelhado
    resumida entre as rodadas. `limiar` padrão: `limiar_de(ref["pesos"])`.
    """
    limiar = limiar_de(ref["pesos"]) if limiar is None else limiar
    n_topicos = len(ref["pesos"])
    pares = [emparelhar(ref["pesos"], r["pesos"]) for r in rodadas]
    temas = []
    for i in range(n_topicos):
        dists = np.array([d[i] for _, d in pares])
        estab = float((dists <= limiar).mean())
        por_periodo = {}
        for p in ref["parcelas"]:
            vals = [r["parcelas"][p][perm[i]] for r, (perm, _) in zip(rodadas, pares)]
            por_periodo[p] = {**resumir_parcelas(vals), "referencia": float(ref["parcelas"][p][i])}
        temas.append({"topico": i, "nome": (nomes or {}).get(i, f"Tópico {i} (sem nome)"),
                      "palavras": ref["palavras"][i][:8], "estabilidade": estab, "instavel": estab < min_estavel,
                      "dist_mediana": float(np.median(dists)), "parcela": por_periodo})
    return {"limiar": limiar, "min_estavel": min_estavel, "n_sementes": len(rodadas), "temas": temas}


def calcular(textos, periodos, n_topicos=6, n_sementes=N_SEMENTES, semente_ref=None, ordem=None, progresso=None):
    """Pipeline completo. `semente_ref=None` escolhe a representativa de 10 (`semente_representativa`).

    `ordem`: períodos (na ordem de exibição); padrão, os que aparecem em `periodos`, em ordem alfabética.
    Devolve o resumo de `resumir` mais "semente_ref", "sementes" e "n_anuncios".
    """
    ordem = list(ordem) if ordem else sorted(set(periodos))
    if semente_ref is None:
        semente_ref, _ = T.semente_representativa(textos, n_topicos)
    ref = treinar(textos, periodos, n_topicos, semente_ref, ordem)
    nomes = T.nomear(dict(enumerate(ref["palavras"])))
    sementes = sementes_fixas(n_sementes)
    rodadas = []
    for i, s in enumerate(sementes, 1):
        rodadas.append(treinar(textos, periodos, n_topicos, s, ordem))
        if progresso:
            progresso(i, len(sementes))
    saida = resumir(ref, rodadas, nomes)
    n_por = {p: int(sum(1 for x in periodos if x == p)) for p in ordem}
    return {**saida, "semente_ref": int(semente_ref), "sementes": [int(s) for s in sementes],
            "n_anuncios": len(textos), "n_por_periodo": n_por, "periodos": ordem}
