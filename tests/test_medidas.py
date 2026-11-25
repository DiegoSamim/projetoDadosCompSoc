import numpy as np
import pandas as pd
import pytest

from hdb.estatistica import wilson
from hdb.medidas import PERIODOS, calcular

TEXTO = "fugiu um escravo"


def df_sintetico():
    linhas = []
    for k, p in enumerate(PERIODOS):
        for j in range(40):
            tipo = "fuga" if j < 25 else "aluguel"
            linhas.append({"id": len(linhas), "periodo": p, "bib": "094170_02", "c_tipo": tipo,
                           "c_sexo": "f" if j % 3 == 0 else "m", "c_idade_min": 20 + k, "c_idade_max": 22 + k,
                           "c_nacoes": ["Mina"] if (tipo == "fuga" and j < 5 * (k + 1)) else [],
                           "c_recompensa": j % 2 == 0, "texto": TEXTO, "bib_": "x",
                           "p_fuga": 0.5 - 0.1 * k, "p_servico": 0.2 + 0.1 * k, "p_ama": 0.1})
    return pd.DataFrame(linhas)


def test_celula_confere_com_calculo_manual():
    df = df_sintetico()
    r = calcular(df)
    p = PERIODOS[1]
    sub = df[(df["periodo"] == p) & (df["c_tipo"] == "fuga")]
    k = int(sub["c_recompensa"].sum())
    est, lo, hi = wilson(k, len(sub))
    c = r[1]["bruta"][p]
    assert c["n"] == len(sub) == 25
    assert c["valor"] == pytest.approx(100 * est) and c["baixo"] == pytest.approx(100 * lo) and c["alto"] == pytest.approx(100 * hi)
    # média de um tema (valor em %)
    assert r[7]["bruta"][p]["valor"] == pytest.approx(100 * df[df["periodo"] == p]["p_fuga"].mean())
    assert r[7]["bruta"][p]["valor"] == pytest.approx(40.0)


def test_estrutura_visoes_diferencas_e_tendencia():
    r = calcular(df_sintetico())
    assert set(r) == set(range(1, 10))
    assert "ajustada" in r[8] and "ajustada" not in r[2] and "ajustada" not in r[6]
    assert set(r[6]["dif"]["bruta"]) == set(PERIODOS[:-1])
    d, lo, hi = r[7]["dif"]["bruta"][PERIODOS[0]]
    assert d == pytest.approx(-30.0) and lo <= d <= hi
    assert r[7]["tendencia"]["bruta"][0] < 0.05 and not np.isnan(r[6]["tendencia"]["jc"][0])
    assert r[4]["bruta"][PERIODOS[0]]["valor"] == pytest.approx(21.0)


def test_so_jc_exclui_bibs_e_tem_n_menor():
    df = df_sintetico()
    df.loc[df["periodo"] == PERIODOS[0], "bib"] = "706744"
    r = calcular(df)
    assert r[6]["bruta"][PERIODOS[0]]["n"] == 40 and r[6]["jc"][PERIODOS[0]]["n"] == 0
