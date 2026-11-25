import random

import numpy as np

from hdb import consenso as C
from hdb.consenso import (calcular, distancias, emparelhar, limiar_de, parcelas_por_periodo, resumir,
                          resumir_parcelas, sementes_fixas)

TEMAS = {
    "fuga": "fugiu escravo fugido fujao matto capitao rastro recompensa gratifica levou fugida",
    "ama": "ama leite amamentar criar crianca parida peito saudavel mulher filho leiteira",
    "domestico": "cozinheira engomar lavar cozinha domestico costura casa servico forno tacho copeira",
}


def corpus(por_tema=40):
    """Textos sintéticos com 3 temas nítidos; período A (tema 3 só em B)."""
    rng = random.Random(1)
    textos, periodos = [], []
    for i, palavras in enumerate(TEMAS.values()):
        lista = palavras.split()
        for j in range(por_tema):
            textos.append(" ".join(rng.choices(lista, k=14)))
            periodos.append("A" if (j % 2 == 0) == (i != 2) else "B")
    return textos, periodos


def pesos(n_topicos=3, v=30, seed=0, pico=0.9):
    """Tema k concentra `pico` da massa em um bloco próprio de palavras."""
    rng = np.random.default_rng(seed)
    m = rng.random((n_topicos, v)) * 0.1
    bloco = v // n_topicos
    for k in range(n_topicos):
        m[k, k * bloco:(k + 1) * bloco] += pico
    return m / m.sum(axis=1, keepdims=True)


def rodada(w, parcela=None):
    k = len(w)
    return {"pesos": w, "parcelas": {"A": np.array(parcela or [1 / k] * k), "B": np.full(k, 1 / k)},
            "palavras": [[f"w{j}" for j in range(5)] for _ in range(k)]}


def test_sementes_fixas_reproduziveis_e_distintas():
    a = sementes_fixas(30)
    assert a == sementes_fixas(30) and len(set(a)) == 30
    assert sementes_fixas(5) != sementes_fixas(5, base=1)


def test_distancia_js_basica():
    w = pesos()
    d = distancias(w, w)
    assert np.allclose(np.diag(d), 0, atol=1e-7) and (d[0, 1] > 0.3) and (d <= 1).all()


def test_emparelhar_recupera_permutacao():
    w = pesos()
    perm = np.array([2, 0, 1])
    ruido = w[perm] + np.random.default_rng(5).random(w.shape) * 0.002
    ruido /= ruido.sum(axis=1, keepdims=True)
    p, d = emparelhar(w, ruido)
    # o tema i da referência está na linha j da rodada onde perm[j] == i
    assert list(p) == [int(np.where(perm == i)[0][0]) for i in range(3)]
    assert d.max() < limiar_de(w)


def test_estabilidade_alta_e_instavel_marcado():
    w = pesos()
    rng = np.random.default_rng(7)
    rodadas = []
    for i in range(10):
        m = w.copy()
        if i % 2 == 0:  # em metade das rodadas, o tema 2 vira outra coisa (distribuição uniforme)
            m[2] = rng.random(m.shape[1])
        m = m / m.sum(axis=1, keepdims=True)
        rodadas.append(rodada(m))
    r = resumir(rodada(w), rodadas, {0: "x", 1: "y", 2: "z"})
    est = [t["estabilidade"] for t in r["temas"]]
    assert est[0] == 1.0 and est[1] == 1.0 and est[2] <= 0.5
    assert [t["instavel"] for t in r["temas"]] == [False, False, True]
    assert r["n_sementes"] == 10 and r["temas"][2]["nome"] == "z"


def test_resumo_por_periodo():
    w = pesos()
    # parcela do tema 0 em A: 0,1 ... 0,5 nas 5 rodadas; as rodadas vêm permutadas (perm conhecida)
    perm = [1, 2, 0]
    rodadas = []
    for v in (0.1, 0.2, 0.3, 0.4, 0.5):
        par = [v, 0.3, 1 - v - 0.3]
        rodadas.append(rodada(w[perm], [par[perm[j]] for j in range(3)]))  # linha j da rodada = tema perm[j] da ref
    ref = rodada(w, [0.2, 0.3, 0.5])
    r = resumir(ref, rodadas)
    a = r["temas"][0]["parcela"]["A"]
    assert abs(a["mediana"] - 0.3) < 1e-9 and a["referencia"] == 0.2
    assert 0.1 <= a["p2_5"] < 0.12 and 0.48 < a["p97_5"] <= 0.5
    assert r["temas"][0]["estabilidade"] == 1.0
    assert resumir_parcelas([1, 2, 3])["mediana"] == 2


def test_parcelas_por_periodo():
    mist = np.array([[1, 0], [0, 1], [0.5, 0.5]])
    out = parcelas_por_periodo(mist, ["A", "B", "A"], ["A", "B", "C"])
    assert np.allclose(out["A"], [0.75, 0.25]) and np.allclose(out["B"], [0, 1]) and "C" not in out


def test_calcular_ponta_a_ponta_com_temas_nitidos():
    textos, periodos = corpus()
    r = calcular(textos, periodos, 3, 3, semente_ref=0, ordem=["A", "B"])
    assert r["n_sementes"] == 3 and len(r["temas"]) == 3 and r["periodos"] == ["A", "B"]
    assert all(t["estabilidade"] >= 0.7 and not t["instavel"] for t in r["temas"])
    assert r["n_por_periodo"] == {"A": 60, "B": 60}
    assert abs(sum(t["parcela"]["A"]["mediana"] for t in r["temas"]) - 1) < 0.05
