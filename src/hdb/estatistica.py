"""Margem de erro e teste de tendência (funções puras, NumPy/SciPy).

Tudo aqui mede o **erro de amostragem** dos anúncios; não mede a instabilidade do modelo de temas (LDA).
"""
import numpy as np
from scipy.stats import norm, spearmanr

SEMENTE = 20251125
NAN3 = (float("nan"),) * 3


def wilson(k, n, z=1.96):
    """Intervalo de Wilson para uma proporção: (proporção, baixo, alto). n = 0 devolve nan."""
    if n <= 0:
        return NAN3
    p = k / n
    z2 = z * z
    centro = (p + z2 / (2 * n)) / (1 + z2 / n)
    meia = z * np.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return (float(p), float(max(0.0, centro - meia)), float(min(1.0, centro + meia)))


def _aplicar(amostras, estatistica):
    """Aplica `estatistica` a cada linha da matriz de reamostras (vetorizado para média e mediana)."""
    if estatistica is np.mean:
        return amostras.mean(axis=1)
    if estatistica is np.median:
        return np.median(amostras, axis=1)
    return np.array([estatistica(linha) for linha in amostras])


def _reamostrar(valores, estatistica, n, rng):
    valores = np.asarray(valores, dtype=float)
    indices = rng.integers(0, len(valores), size=(n, len(valores)))
    return _aplicar(valores[indices], estatistica)


def bootstrap_ic(valores, estatistica, n=2000, semente=SEMENTE):
    """IC de 95% por bootstrap percentil: (estimativa, baixo, alto). Amostra vazia devolve nan."""
    valores = np.asarray(valores, dtype=float)
    if len(valores) == 0:
        return NAN3
    rng = np.random.default_rng(semente)
    reamostras = _reamostrar(valores, estatistica, n, rng)
    baixo, alto = np.percentile(reamostras, [2.5, 97.5])
    return (float(estatistica(valores)), float(baixo), float(alto))


def diferenca_ic(grupo_primeiro, grupo_ultimo, estatistica, n=2000, semente=SEMENTE):
    """Diferença (último − primeiro) com IC de 95% por bootstrap, reamostrando cada grupo separadamente."""
    a = np.asarray(grupo_primeiro, dtype=float)
    b = np.asarray(grupo_ultimo, dtype=float)
    if len(a) == 0 or len(b) == 0:
        return NAN3
    rng = np.random.default_rng(semente)
    dif = _reamostrar(b, estatistica, n, rng) - _reamostrar(a, estatistica, n, rng)
    baixo, alto = np.percentile(dif, [2.5, 97.5])
    return (float(estatistica(b) - estatistica(a)), float(baixo), float(alto))


def cochran_armitage(ks, ns, escores=None):
    """Teste de tendência de Cochran–Armitage: (z, p bilateral). (nan, nan) se não houver variância."""
    k = np.asarray(ks, dtype=float)
    n = np.asarray(ns, dtype=float)
    s = np.arange(1, len(k) + 1, dtype=float) if escores is None else np.asarray(escores, dtype=float)
    N = n.sum()
    if N == 0:
        return (float("nan"), float("nan"))
    p = k.sum() / N
    var = p * (1 - p) * ((n * s * s).sum() - (n * s).sum() ** 2 / N)
    if var <= 0:
        return (float("nan"), float("nan"))
    z = float((s * (k - n * p)).sum() / np.sqrt(var))
    return (z, float(2 * (1 - norm.cdf(abs(z)))))


def spearman_tendencia(periodos, valores):
    """Correlação de Spearman entre a ordem do período e o valor: (rho, p). nan se n < 3 ou sem variação."""
    x = np.asarray(periodos, dtype=float)
    y = np.asarray(valores, dtype=float)
    if len(x) < 3 or len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        return (float("nan"), float("nan"))
    rho, p = spearmanr(x, y)
    return (float(rho), float(p))


def fdr_bh(pvalores):
    """P ajustados de Benjamini–Hochberg, na ordem da entrada; nan fica nan e não conta."""
    p = np.asarray(pvalores, dtype=float)
    saida = np.full(p.shape, np.nan)
    ok = ~np.isnan(p)
    m = int(ok.sum())
    if m == 0:
        return saida
    valores = p[ok]
    ordem = np.argsort(valores)
    ajust = valores[ordem] * m / np.arange(1, m + 1)
    ajust = np.minimum.accumulate(ajust[::-1])[::-1]
    resultado = np.empty(m)
    resultado[ordem] = np.minimum(ajust, 1.0)
    saida[ok] = resultado
    return saida
