import math

from hdb.afirmacoes import AFIRMACOES, formatar, quadro

P = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
NAN = float("nan")


def celulas(valores, ns=(100, 100, 100, 100)):
    return {p: {"n": n, "n_ef": float(n), "valor": v, "baixo": v - 1, "alto": v + 1} for p, v, n in zip(P, valores, ns)}


def medida(bruta, jc=None, aj=None, dif=None, p=1e-6, ns=(100,) * 4, ns_jc=None, tema=False):
    """Uma medida sintética. `dif` = {visão: (d, lo, hi)} aplicado a qualquer base; padrão: último − base com IC ±3."""
    r = {"bruta": celulas(bruta, ns), "jc": celulas(jc or bruta, ns_jc or ns), "dif": {}, "tendencia": {"bruta": (p, 0.0), "jc": (p, 0.0)}}
    visoes = {"bruta": bruta, "jc": jc or bruta}
    if tema:
        r["ajustada"] = celulas(aj or bruta, ns)
        visoes["ajustada"] = aj or bruta
    for v, vals in visoes.items():
        padrao = (vals[-1] - vals[0], vals[-1] - vals[0] - 3, vals[-1] - vals[0] + 3)
        d = (dif or {}).get(v, padrao)
        r["dif"][v] = {b: d for b in P[:-1]}
    return r


def todos(primeiro, **kw):
    """Resultados das 9 afirmações: a de id 1 é `primeiro`; as outras são constantes sem efeito."""
    plana = medida([50, 50, 50, 50], p=0.9)
    plana_tema = medida([50, 50, 50, 50], p=0.9, tema=True)
    return {i: (primeiro if i == 1 else plana_tema if i >= 7 else plana) for i in range(1, 10)}


def linha(res, i=1):
    return quadro(res)[i - 1]


def test_lista_fixa_de_nove():
    assert [a[0] for a in AFIRMACOES] == list(range(1, 10))
    assert [a[2] for a in AFIRMACOES][:5] == ["dentro do tipo"] * 5
    assert AFIRMACOES[5][2] == "mistura da amostra" and AFIRMACOES[8][2] == "tema (acompanha o tipo)"


def test_queda_gradual_e_coerente_e_sustentada():
    l = linha(todos(medida([60, 50, 40, 30])))
    assert l["veredito"] == "sustentada" and l["forma"] == "gradual"
    assert l["base_bruta"] == l["base_jc"] == "antes de 1831"
    assert l["valor_base_bruta"] == 60 and l["valor_ultimo_bruta"] == 30


def test_sinal_muda_so_com_jc_nao_sustentada():
    r = medida([60, 50, 40, 30], jc=[40, 45, 50, 55])
    l = linha(todos(r))
    assert l["veredito"] == "não sustentada" and "só JC" in l["motivo"]


def test_ic_com_zero_so_no_jc_e_parcial():
    r = medida([60, 50, 40, 30], dif={"jc": (-5, -12, 2)})
    l = linha(todos(r))
    assert l["veredito"] == "parcial" and "só JC" in l["motivo"]


def test_base_com_n_pequeno_recua_e_quadro_mostra_a_base():
    r = medida([60, 50, 40, 30], ns=(100, 100, 100, 100), ns_jc=(10, 100, 100, 100))
    l = linha(todos(r))
    assert l["base_bruta"] == "antes de 1831" and l["base_jc"] == "1831–1850"
    assert l["veredito"] in ("sustentada", "parcial", "não sustentada")
    t = formatar(quadro(todos(r)))
    assert "bruta: antes de 1831; só JC: 1831–1850" in t


def test_sem_base_valida_e_fragil():
    r = medida([60, 50, 40, 30], ns=(10, 10, 10, 100))
    assert linha(todos(r))["veredito"] == "frágil"
    r = medida([60, 50, 40, 30], ns=(100, 100, 100, 20))
    assert linha(todos(r))["veredito"] == "frágil"


def test_tema_bruta_em_queda_e_ajustada_plana_nao_sustentada():
    r = medida([46, 24, 20, 25], aj=[25, 24, 26, 25], tema=True, dif={"bruta": (-21, -29, -13), "jc": (-21, -29, -13), "ajustada": (0.5, -3, 4)})
    res = todos(medida([60, 50, 40, 30]))
    res[7] = r
    l = linha(res, 7)
    assert l["veredito"] == "não sustentada" and l["natureza"].startswith("tema")
    assert "ajustada" in l["motivo"]


def test_um_degrau_e_gradual():
    assert linha(todos(medida([60, 60, 60, 30])))["forma"] == "um degrau"
    assert linha(todos(medida([60, 50, 40, 30])))["forma"] == "gradual"


def test_afirmacao_6_a_9_sustentada_leva_sufixo():
    res = todos(medida([60, 50, 40, 30]))
    res[6] = medida([60, 50, 40, 30])
    res[9] = medida([60, 50, 40, 30], tema=True)
    q = quadro(res)
    assert q[5]["veredito"] == "sustentada (ver natureza)"
    assert q[8]["veredito"] == "sustentada (ver natureza)"


def test_direcao_contraria_nao_sustentada():
    l = linha(todos(medida([30, 40, 50, 60])))  # afirmação 1 espera queda
    assert l["veredito"] == "não sustentada"


def test_p_ajustado_alto_vira_parcial():
    res = {i: medida([60, 50, 40, 30], p=0.5, tema=i >= 7) for i in range(1, 10)}
    l = linha(res)
    assert l["veredito"] == "parcial" and l["p_ajustado"] >= 0.05


def test_formatar_tem_uma_linha_por_afirmacao():
    t = formatar(quadro(todos(medida([60, 50, 40, 30]))))
    assert t.count("\n") == 10 and "A recompensa nas fugas diminui" in t and "**sustentada**" in t


def test_tema_cuja_tendencia_some_ao_igualar_a_mistura_nao_e_sustentada():
    """Tema: o IC da visão ajustada com zero (mesmo sinal ou não) => era mistura de tipos, não mudança de conteúdo."""
    res = todos(medida([60, 50, 40, 30]))
    res[7] = medida([60, 50, 40, 30], tema=True, dif={"ajustada": (-2, -8, 4)})
    l = linha(res, 7)
    assert l["veredito"].startswith("não sustentada") and "mistura de tipos" in l["motivo"]
    res[7] = medida([60, 50, 40, 30], tema=True, dif={"ajustada": (0.0, -4, 4)})
    assert linha(res, 7)["veredito"].startswith("não sustentada")
    res[7] = medida([60, 50, 40, 30], tema=True, dif={"ajustada": (-6, -9, -3)})  # sobrevive à mistura
    assert linha(res, 7)["veredito"].startswith("sustentada")
