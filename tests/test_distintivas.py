from collections import Counter

from hdb.distintivas import palavras_distintivas


def contagens():
    comum = {"escravo": 60, "anos": 40}
    return {
        "A": Counter({**comum, "fugiu": 30, "matto": 8}),
        "B": Counter({**comum, "leite": 28, "ama": 9}),
        "C": Counter({**comum, "vende": 25}),
    }


def test_palavra_exclusiva_sai_no_topo_e_a_comum_nao_sai():
    r = palavras_distintivas(contagens())
    assert r["A"][0][0] == "fugiu" and r["A"][0][2] == 30 and r["A"][0][1] >= 1.96
    assert [p for p, _, _ in r["B"]][:2] == ["leite", "ama"]
    assert all(p not in ("escravo", "anos") for g in r.values() for p, _, _ in g)
    assert "fugiu" not in [p for p, _, _ in r["B"]]


def test_ordem_decrescente_n_e_z_min():
    r = palavras_distintivas(contagens(), n=1)
    assert all(len(v) <= 1 for v in r.values())
    zs = [z for _, z, _ in palavras_distintivas(contagens())["A"]]
    assert zs == sorted(zs, reverse=True)
    assert all(v == [] for v in palavras_distintivas(contagens(), z_min=1000).values())


def test_prior_explicito_e_vazio():
    prior = Counter({"fugiu": 5, "matto": 5, "leite": 5, "ama": 5, "vende": 5, "escravo": 5, "anos": 5})
    assert palavras_distintivas(contagens(), prior=prior)["A"][0][0] == "fugiu"
    assert palavras_distintivas({"A": Counter(), "B": Counter()}) == {"A": [], "B": []}
