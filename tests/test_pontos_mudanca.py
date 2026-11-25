import numpy as np
import pandas as pd

from hdb.afirmacoes import formatar, quadro
from hdb.pontos_mudanca import calcular_pontos, ponto_mudanca, serie_anual, texto_ponto

from test_afirmacoes import medida, todos


def simular(rng, anos, n, p_antes, p_depois, corte):
    ano = np.repeat(anos, n)
    p = np.where(ano < corte, p_antes, p_depois)
    return ano, (rng.random(len(ano)) < p).astype(float)


def test_ponto_conhecido_e_recuperado_em_90_por_cento():
    rng = np.random.default_rng(1)
    certos = 0
    for _ in range(200):
        ano, v = simular(rng, np.arange(1820, 1860), 60, 0.6, 0.2, 1840)
        r = ponto_mudanca(ano, v, rep=100)
        certos += r["definido"] and abs(r["ano"] - 1840) <= 1
    assert certos >= 180


def test_ic_e_datas_legais_cobertas():
    rng = np.random.default_rng(2)
    ano, v = simular(rng, np.arange(1840, 1862), 80, 0.7, 0.3, 1850)
    r = ponto_mudanca(ano, v, rep=300)
    assert r["definido"] and r["baixo"] <= 1850 <= r["alto"] and r["cobre"] == [1850]
    assert r["antes"] > 0.6 and r["depois"] < 0.4 and r["p"] < 0.01
    assert texto_ponto(r) == str(r["ano"]) and texto_ponto(r, com_ic=True).startswith(str(r["ano"]))


def test_serie_sem_mudanca_nao_define_ponto():
    rng = np.random.default_rng(3)
    ano, v = simular(rng, np.arange(1820, 1860), 60, 0.4, 0.4, 1840)
    r = ponto_mudanca(ano, v, rep=300)
    assert not r["definido"] and texto_ponto(r) == "sem ponto"
    assert r["motivo"]


def test_anos_com_n_pequeno_nao_entram_no_ajuste():
    rng = np.random.default_rng(4)
    ano, v = simular(rng, np.arange(1840, 1860), 60, 0.6, 0.2, 1850)
    # três anúncios isolados em 1800, todos 1: se entrassem, puxariam o ponto para o começo
    ano = np.concatenate([[1800] * 3, ano])
    v = np.concatenate([[1.0] * 3, v])
    r = ponto_mudanca(ano, v, rep=200)
    assert r["anos_fora"] == [1800] and abs(r["ano"] - 1850) <= 1
    s = serie_anual(ano, v)
    assert not s.loc[s["ano"] == 1800, "ok"].iloc[0] and s["ok"].sum() == 20


def test_poucos_anos_validos_nao_quebra():
    r = ponto_mudanca([1850] * 30, [1.0] * 30, rep=50)
    assert not r["definido"] and r["ano"] is None


def test_peso_zero_sai_e_peso_ajustado_recupera_ponto():
    rng = np.random.default_rng(5)
    ano, v = simular(rng, np.arange(1840, 1860), 80, 0.7, 0.2, 1850)
    w = np.where(rng.random(len(ano)) < 0.2, 0.0, rng.uniform(0.5, 2.0, len(ano)))
    r = ponto_mudanca(ano, v, w, rep=200)
    assert r["definido"] and abs(r["ano"] - 1850) <= 1


def _df(rng, so_jc_tem_mudanca):
    """Corpus sintético: fugas com recompensa caindo em 1850; os anúncios do bib de fora do JC fazem a queda se `not so_jc_tem_mudanca`."""
    linhas = []
    for ano in range(1835, 1866):
        for i in range(60):
            fora = i < 20
            depois = ano >= 1850
            if so_jc_tem_mudanca:
                p = 0.7 if not depois else 0.2
            else:   # o degrau existe só nos anúncios de fora do JC
                p = (0.2 if depois else 0.7) if fora else 0.45
            linhas.append({"ano": ano, "periodo": "1831–1850" if ano < 1850 else "1850–1871", "bib": "706744" if fora else "000001",
                           "c_tipo": "fuga", "c_recompensa": bool(rng.random() < p), "c_sexo": None, "c_nacoes": [],
                           "c_idade_min": None, "c_idade_max": None, "texto": "", "marcas": False,
                           "p_fuga": 0.5, "p_servico": 0.1, "p_ama": 0.1})
    return pd.DataFrame(linhas)


def test_calcular_pontos_tres_visoes_e_so_jc():
    pt = calcular_pontos(_df(np.random.default_rng(6), True), rep=200)
    r = pt[1]
    assert set(r) >= {"bruta", "jc", "ajustada", "serie"}
    assert all(r[v]["definido"] and abs(r[v]["ano"] - 1850) <= 1 for v in ("bruta", "jc", "ajustada"))
    assert r["serie"]["jc"]["n"].max() == 40

    pt = calcular_pontos(_df(np.random.default_rng(7), False), rep=200)
    assert pt[1]["bruta"]["definido"] and not pt[1]["jc"]["definido"]


def test_coluna_do_quadro_e_motivo_de_jornal():
    ok = {"definido": True, "ano": 1850, "baixo": 1849, "alto": 1851, "p": 0.001, "cobre": [1850]}
    jc = {"definido": True, "ano": 1851, "baixo": 1849, "alto": 1853, "p": 0.001, "cobre": [1850]}
    sem = {"definido": False, "ano": None, "baixo": None, "alto": None, "p": 0.4, "cobre": []}
    res = todos(medida([60, 50, 40, 30]))
    sem_pontos = quadro(res)
    assert sem_pontos[0]["ano_mudanca"] == "–"
    q = quadro(res, {1: {"bruta": ok, "jc": jc, "ajustada": ok}, 2: {"bruta": ok, "jc": sem, "ajustada": ok},
                     3: {"bruta": sem, "jc": sem, "ajustada": sem}})
    assert [q[i]["ano_mudanca"] for i in range(3)] == ["1850 (1851)", "1850 (sem ponto)", "sem ponto (sem ponto)"]
    assert "Possível efeito de jornal" in q[1]["motivo"] and "jornal" not in q[0]["motivo"] and "jornal" not in q[2]["motivo"]
    assert [l["veredito"] for l in q] == [l["veredito"] for l in sem_pontos]   # o veredito não muda
    t = formatar(q)
    assert "Ano da mudança" in t and "1850 (1851)" in t
