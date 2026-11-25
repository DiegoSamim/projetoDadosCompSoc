import math

import numpy as np
import pytest

from hdb.estatistica import bootstrap_ic, cochran_armitage, diferenca_ic, fdr_bh, spearman_tendencia, wilson


def test_wilson_valor_conhecido():
    p, baixo, alto = wilson(5, 20)
    assert p == 0.25
    assert baixo == pytest.approx(0.112, abs=0.002) and alto == pytest.approx(0.469, abs=0.002)


def test_wilson_extremos_e_vazio():
    p, baixo, alto = wilson(0, 10)
    assert p == 0 and baixo == 0 and 0 < alto < 1
    p, baixo, alto = wilson(10, 10)
    assert p == 1 and alto == 1 and 0 < baixo < 1
    assert all(math.isnan(v) for v in wilson(0, 0))


def qui_quadrado_tendencia(k, n, s):
    k, n, s = map(lambda v: np.asarray(v, dtype=float), (k, n, s))
    K, N = k.sum(), n.sum()
    num = ((s * k).sum() - K / N * (s * n).sum()) ** 2
    den = (K / N) * (1 - K / N) * ((s ** 2 * n).sum() - (s * n).sum() ** 2 / N)
    return num / den


@pytest.mark.parametrize("ks, ns", [([5, 12, 25, 40], [100, 100, 100, 100]), ([20, 21, 19, 20], [100, 100, 100, 100])])
def test_cochran_armitage_bate_com_implementacao_independente(ks, ns):
    z, p = cochran_armitage(ks, ns)
    chi2 = qui_quadrado_tendencia(ks, ns, [1, 2, 3, 4])
    assert z ** 2 == pytest.approx(chi2)
    assert p == pytest.approx(math.erfc(math.sqrt(chi2 / 2)))  # p bilateral de z


def test_cochran_armitage_sinal_e_significancia():
    z, p = cochran_armitage([5, 12, 25, 40], [100] * 4)
    assert z > 0 and p < 0.001
    z, p = cochran_armitage([20, 21, 19, 20], [100] * 4)
    assert p > 0.5


def test_cochran_armitage_sem_variancia():
    assert all(math.isnan(v) for v in cochran_armitage([0, 0, 0], [10, 10, 10]))
    assert all(math.isnan(v) for v in cochran_armitage([10, 10], [10, 10]))
    assert all(math.isnan(v) for v in cochran_armitage([0, 0], [0, 0]))


def test_fdr_bh_exemplo_a_mao_e_nan():
    assert fdr_bh([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.02, 0.04, 0.04, 0.02])
    r = fdr_bh([0.01, float("nan"), 0.04, 0.03, 0.005])
    assert math.isnan(r[1])
    assert [r[0], r[2], r[3], r[4]] == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_bootstrap_reprodutivel_e_estimativa_dentro_do_ic():
    x = np.random.default_rng(1).normal(30, 5, 80)
    a = bootstrap_ic(x, np.mean)
    assert a == bootstrap_ic(x, np.mean)
    est, baixo, alto = bootstrap_ic(x, np.median)
    assert baixo <= est <= alto
    assert bootstrap_ic(x, np.mean, semente=1) != a


def test_bootstrap_amostra_constante_e_degenerada():
    assert bootstrap_ic([7.0] * 20, np.mean) == (7.0, 7.0, 7.0)


def test_bootstrap_funcao_generica():
    est, baixo, alto = bootstrap_ic(np.arange(50.0), lambda v: float(np.max(v)))
    assert baixo <= est <= alto == 49


def test_diferenca_ic_sinal():
    primeiro = np.random.default_rng(2).normal(10, 1, 100)
    ultimo = np.random.default_rng(3).normal(15, 1, 100)
    d, baixo, alto = diferenca_ic(primeiro, ultimo, np.mean)
    assert d > 4 and 0 < baixo <= d <= alto
    d, baixo, alto = diferenca_ic(ultimo, primeiro, np.median)
    assert d < -4 and alto < 0


def test_spearman_tendencia():
    rho, p = spearman_tendencia([1, 2, 3, 4], [1.0, 2.0, 3.5, 9.0])
    assert rho == pytest.approx(1.0)
    rho, p = spearman_tendencia([1, 2, 3, 4], [9.0, 5.0, 2.0, 1.0])
    assert rho == pytest.approx(-1.0)
    assert all(math.isnan(v) for v in spearman_tendencia([1, 2, 3], [5, 5, 5]))
    assert all(math.isnan(v) for v in spearman_tendencia([1, 2], [1, 2]))
