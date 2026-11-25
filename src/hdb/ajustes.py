"""Ajustes de robustez: padronização da mistura de tipos, visão "só Jornal do Commercio" e bootstrap ponderado.

Funções puras (NumPy/pandas). Como em estatistica.py, medem o erro de amostragem dos anúncios,
não a instabilidade do modelo de temas.
"""
import numpy as np
import pandas as pd

from hdb.estatistica import NAN3, SEMENTE

TIPOS_AJUSTE = ("fuga", "aluguel", "venda", "ama_de_leite")
BIBS_FORA_JC = ("094170_01", "706744")


def pesos_mistura(df, tipos=TIPOS_AJUSTE, col_tipo="c_tipo", col_periodo="periodo"):
    """Peso de cada anúncio = P(tipo no conjunto todo) / P(tipo no seu período), só sobre `tipos`.

    Padronização direta: com esses pesos, a mistura de tipos é a mesma em todos os períodos.
    Anúncios de outros tipos (compra, etc.) ou sem período recebem peso 0. Devolve Series alinhada ao df.
    """
    pesos = pd.Series(0.0, index=df.index)
    sub = df[df[col_tipo].isin(tipos) & df[col_periodo].notna()]
    if sub.empty:
        return pesos
    global_ = sub[col_tipo].value_counts(normalize=True)
    por_periodo = sub.groupby(col_periodo)[col_tipo].value_counts(normalize=True)
    chaves = pd.MultiIndex.from_arrays([sub[col_periodo], sub[col_tipo]])
    no_periodo = por_periodo.reindex(chaves).to_numpy()
    pesos.loc[sub.index] = sub[col_tipo].map(global_).to_numpy() / no_periodo
    return pesos


def so_jc(df, bibs_excluidos=BIBS_FORA_JC, col_bib="bib"):
    """Exclui os bibs que não são do Jornal do Commercio."""
    return df[~df[col_bib].isin(bibs_excluidos)]


def n_efetivo(pesos):
    """Tamanho efetivo da amostra ponderada: (Σw)² / Σw². Com pesos iguais, é n."""
    w = np.asarray(pesos, dtype=float)
    soma2 = (w * w).sum()
    return float(w.sum() ** 2 / soma2) if soma2 > 0 else 0.0


def _boot_medias(valores, pesos, n, rng):
    indices = rng.integers(0, len(valores), size=(n, len(valores)))
    w = pesos[indices]
    return (w * valores[indices]).sum(axis=1) / w.sum(axis=1)


def _limpar(valores, pesos):
    v = np.asarray(valores, dtype=float)
    w = np.asarray(pesos, dtype=float)
    ok = w > 0
    return v[ok], w[ok]


def media_ponderada_ic(valores, pesos, grupos, n=2000, semente=SEMENTE):
    """Média ponderada por grupo com IC de 95% por bootstrap: {grupo: (estimativa, baixo, alto)}.

    Reamostra anúncios com reposição, levando o peso junto. Grupo sem anúncios de peso > 0 devolve nan.
    """
    valores, pesos, grupos = np.asarray(valores, dtype=float), np.asarray(pesos, dtype=float), np.asarray(grupos)
    rng = np.random.default_rng(semente)
    saida = {}
    for g in dict.fromkeys(grupos.tolist()):
        v, w = _limpar(valores[grupos == g], pesos[grupos == g])
        if len(v) == 0:
            saida[g] = NAN3
            continue
        baixo, alto = np.percentile(_boot_medias(v, w, n, rng), [2.5, 97.5])
        saida[g] = (float(np.average(v, weights=w)), float(baixo), float(alto))
    return saida


def diferenca_ponderada_ic(valores_primeiro, pesos_primeiro, valores_ultimo, pesos_ultimo, n=2000, semente=SEMENTE):
    """Diferença das médias ponderadas (último − primeiro) com IC de 95% por bootstrap dos dois grupos."""
    a, wa = _limpar(valores_primeiro, pesos_primeiro)
    b, wb = _limpar(valores_ultimo, pesos_ultimo)
    if len(a) == 0 or len(b) == 0:
        return NAN3
    rng = np.random.default_rng(semente)
    dif = _boot_medias(b, wb, n, rng) - _boot_medias(a, wa, n, rng)
    baixo, alto = np.percentile(dif, [2.5, 97.5])
    return (float(np.average(b, weights=wb) - np.average(a, weights=wa)), float(baixo), float(alto))


def _inclinacoes(x, y, w):
    """Inclinação de mínimos quadrados ponderados de y contra x; x e w podem ter uma linha por embaralhamento."""
    x, w = np.atleast_2d(x), np.atleast_2d(w)
    sw = w.sum(axis=1)
    mx = (w * x).sum(axis=1) / sw
    my = (w * y).sum(axis=1) / sw
    dx = x - mx[:, None]
    den = (w * dx * dx).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (w * dx * (y - my[:, None])).sum(axis=1) / den


def inclinacao_permutacao(periodos, valores, pesos, tipos, n=1000, semente=SEMENTE):
    """Inclinação ponderada da parcela contra o escore do período e p por permutação: (inclinação, p).

    Dentro de cada tipo embaralha-se o período entre os anúncios (o peso acompanha o período, pois depende
    de tipo e período); p = proporção das |inclinações| embaralhadas >= |observada|. Anúncios de peso 0 saem.
    """
    x = np.asarray(periodos, dtype=float)
    y = np.asarray(valores, dtype=float)
    w = np.asarray(pesos, dtype=float)
    t = np.asarray(tipos)
    ok = w > 0
    x, y, w, t = x[ok], y[ok], w[ok], t[ok]
    if len(x) < 3 or len(np.unique(x)) < 2:
        return (float("nan"), float("nan"))
    obs = float(_inclinacoes(x, y, w)[0])
    rng = np.random.default_rng(semente)
    ordem = np.tile(np.arange(len(x)), (n, 1))
    for tipo in np.unique(t):
        pos = np.flatnonzero(t == tipo)
        sorteio = np.argsort(rng.random((n, len(pos))), axis=1)
        ordem[:, pos] = pos[sorteio]
    perm = _inclinacoes(x[ordem], y, w[ordem])
    p = float(np.mean(np.abs(perm) >= abs(obs) - 1e-12))
    return (obs, p)
