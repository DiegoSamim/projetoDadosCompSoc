import numpy as np
import pandas as pd
import pytest

from hdb.ajustes import (diferenca_ponderada_ic, inclinacao_permutacao, media_ponderada_ic, n_efetivo,
                         pesos_mistura, so_jc)

PERIODOS = ["p1", "p2", "p3", "p4"]
TIPOS = ["fuga", "aluguel", "venda", "ama_de_leite"]


def corpus_sintetico():
    """Mistura de tipos diferente em cada período, mais compra e outro tipo."""
    mistura = {"p1": [10, 5, 20, 5], "p2": [30, 10, 10, 2], "p3": [8, 40, 4, 8], "p4": [25, 25, 25, 10]}
    linhas = []
    for p, contagens in mistura.items():
        for tipo, k in zip(TIPOS, contagens):
            linhas += [(p, tipo, "094170_02")] * k
        linhas += [(p, "compra", "706744")] * 7 + [(p, "outro", "094170_02")] * 2
    return pd.DataFrame(linhas, columns=["periodo", "c_tipo", "bib"])


def test_mistura_ponderada_igual_em_todos_os_periodos():
    df = corpus_sintetico()
    df["w"] = pesos_mistura(df)
    sub = df[df["w"] > 0]
    por = sub.groupby(["periodo", "c_tipo"])["w"].sum().unstack()
    prop = por.div(por.sum(axis=1), axis=0)
    esperado = sub["c_tipo"].value_counts(normalize=True)
    for p in PERIODOS:
        for tipo in TIPOS:
            assert prop.loc[p, tipo] == pytest.approx(esperado[tipo], abs=1e-9)


def test_compra_e_outros_recebem_peso_zero():
    df = corpus_sintetico()
    w = pesos_mistura(df)
    assert (w[df["c_tipo"].isin(["compra", "outro"])] == 0).all()
    assert (w[df["c_tipo"].isin(TIPOS)] > 0).all()
    assert w.index.equals(df.index)


def test_so_jc_remove_exatamente_os_dois_bibs():
    df = corpus_sintetico()
    df.loc[df.index[:3], "bib"] = "094170_01"
    r = so_jc(df)
    assert not r["bib"].isin(["094170_01", "706744"]).any()
    assert len(r) == (~df["bib"].isin(["094170_01", "706744"])).sum()
    assert set(r["bib"]) == {"094170_02"}


def test_pesos_iguais_dao_media_simples_e_n_efetivo_n():
    rng = np.random.default_rng(1)
    v = rng.random(60)
    g = np.repeat(["a", "b", "c"], 20)
    r = media_ponderada_ic(v, np.full(60, 2.5), g, n=200)
    for k in "abc":
        assert r[k][0] == pytest.approx(np.average(v[g == k]))
        assert r[k][1] <= r[k][0] <= r[k][2]
    assert n_efetivo(np.full(37, 0.3)) == pytest.approx(37)


def test_n_efetivo_menor_com_peso_dominante():
    w = np.ones(50)
    w[0] = 100
    assert n_efetivo(w) < 10
    assert n_efetivo([]) == 0


def test_bootstrap_reprodutivel_com_a_mesma_semente():
    rng = np.random.default_rng(2)
    v, w = rng.random(40), rng.random(40) + 0.5
    g = np.array(["a"] * 40)
    assert media_ponderada_ic(v, w, g) == media_ponderada_ic(v, w, g)
    assert media_ponderada_ic(v, w, g, semente=1) != media_ponderada_ic(v, w, g, semente=2)
    d1 = diferenca_ponderada_ic(v[:20], w[:20], v[20:], w[20:])
    assert d1 == diferenca_ponderada_ic(v[:20], w[:20], v[20:], w[20:])
    assert d1[1] <= d1[0] <= d1[2]


def test_diferenca_ponderada_detecta_diferenca():
    a, b = np.full(30, 0.2), np.full(30, 0.8)
    dif, lo, hi = diferenca_ponderada_ic(a, np.ones(30), b, np.ones(30))
    assert dif == pytest.approx(0.6) and lo > 0


def test_permutacao_detecta_inclinacao_construida():
    rng = np.random.default_rng(3)
    periodos = np.repeat([1, 2, 3, 4], 50)
    tipos = np.tile(["fuga", "aluguel"], 100)
    valores = 0.1 * periodos + rng.normal(0, 0.1, 200)
    incl, p = inclinacao_permutacao(periodos, valores, np.ones(200), tipos)
    assert incl == pytest.approx(0.1, abs=0.03)
    assert p < 0.01


def test_permutacao_nao_detecta_em_dados_embaralhados():
    rng = np.random.default_rng(4)
    periodos = np.repeat([1, 2, 3, 4], 50)
    tipos = np.tile(["fuga", "aluguel"], 100)
    valores = rng.normal(0, 1, 200)
    pesos = rng.random(200) + 0.5
    _, p = inclinacao_permutacao(periodos, valores, pesos, tipos)
    assert p > 0.1
    assert inclinacao_permutacao(periodos, valores, pesos, tipos) == (_, p)


def test_permutacao_vazia_ou_sem_variacao():
    incl, p = inclinacao_permutacao([1, 1, 1], [0.1, 0.2, 0.3], [1, 1, 1], ["a"] * 3)
    assert np.isnan(incl) and np.isnan(p)
