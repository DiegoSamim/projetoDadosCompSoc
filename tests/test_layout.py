from hdb import layout


def palavra(t, x, y=100, w=40, h=15, c=90, b=1, p=1, l=1):
    return {"t": t, "x": x, "y": y, "w": w, "h": h, "c": c, "b": b, "p": p, "l": l}


def seg(x0, x1, y=100, n=3, linha=(1, 1, 1), **resto):
    return {"x0": x0, "x1": x1, "y0": y - 7, "y1": y + 7, "y": y, "h": 15, "n": n, "texto": "texto " * n,
            "conf": 90.0, "linha": linha, **resto}


def test_corta_a_linha_nos_espacos_grandes():
    palavras = [palavra("a", 0), palavra("b", 50), palavra("c", 100),  # espaços de 10 px
                palavra("d", 400), palavra("e", 450)]  # vão de 260 px entre colunas
    segs = layout.segmentos(palavras, gap=35)
    assert [s["texto"] for s in segs] == ["a b c", "d e"]
    assert (segs[1]["x0"], segs[1]["x1"], segs[1]["n"]) == (400, 490, 2)


def test_linhas_diferentes_nao_se_misturam():
    segs = layout.segmentos([palavra("a", 0, l=1), palavra("b", 50, l=2), palavra("c", 50, l=1)], gap=35)
    assert sorted(s["texto"] for s in segs) == ["a c", "b"]


def test_fio_vertical_fecha_o_vao_mas_corta():
    palavras = [palavra("a", 0), palavra("|", 45, w=3), palavra("b", 55)]  # sem vão: o fio ocupa o espaço
    assert [s["texto"] for s in layout.segmentos(palavras, gap=35)] == ["a |", "b"]


def segmentos_de_colunas(x0s, linhas, apoio_extra=None):
    """`linhas` linhas de segmentos largos (200 px) começando em cada x0."""
    return [seg(x, x + 200, y=20 * i) for i in range(linhas) for x in x0s]


def test_bordas_com_apoio_relativo():
    segs = segmentos_de_colunas([100, 500, 900], 100)
    segs += [seg(700, 900, y=20 * i) for i in range(20)]  # borda espúria: apoio 20 contra 100 (mínimo 35%)
    assert layout.bordas_de_colunas(segs) == [100, 500, 900]


def test_borda_com_apoio_proporcional_numa_pagina_curta():
    segs = segmentos_de_colunas([100, 500], 12) + [seg(300, 500, y=20 * i) for i in range(3)]
    assert layout.bordas_de_colunas(segs) == [100, 500]  # 3 < apoio mínimo (10)


def test_tolerancia_agrupa_recuos_e_ignora_segmentos_estreitos():
    segs = [seg(100 + (i % 3) * 10, 400, y=20 * i) for i in range(30)] + [seg(600, 640, y=20 * i) for i in range(30)]
    assert layout.bordas_de_colunas(segs) == [110]


def test_colunas_cobrem_a_pagina():
    faixas = layout.colunas([100, 500, 900], 1300)
    assert faixas[0][0] == 0 and faixas[-1][1] == 1300
    assert all(a[1] == b[0] for a, b in zip(faixas, faixas[1:]))
    assert layout.colunas([], 1300) == [(0, 1300)]


def test_ordem_de_leitura_coluna_a_coluna_e_de_cima_para_baixo():
    faixas = [(0, 500), (500, 1000)]
    segs = [seg(520, 900, y=50, linha=(1, 1, 1)), seg(20, 400, y=300, linha=(1, 1, 2)),
            seg(20, 400, y=50, linha=(2, 1, 1)), seg(520, 900, y=300, linha=(2, 1, 2))]
    ordem = layout.atribuir_colunas(segs, faixas)
    assert [(s["coluna"], s["y"]) for s in ordem] == [(0, 50), (0, 300), (1, 50), (1, 300)]


def test_segmento_largo_entra_na_coluna_onde_comeca():
    faixas = [(0, 500), (500, 1000)]
    titulo = seg(150, 950, y=10, linha=(9, 1, 1))  # cruza as duas colunas, centro na 2ª
    corpo = seg(20, 400, y=100, linha=(1, 1, 1))
    ordem = layout.atribuir_colunas([corpo, titulo], faixas)
    assert [(s["coluna"], s["largo"]) for s in ordem] == [(0, True), (0, False)]


def test_pedacos_da_mesma_linha_na_mesma_coluna_sao_reunidos():
    faixas = [(0, 500), (500, 1000)]
    a, b = seg(20, 150, linha=(1, 1, 1), n=2), seg(200, 400, linha=(1, 1, 1), n=3)
    ordem = layout.atribuir_colunas([a, b], faixas)
    assert len(ordem) == 1 and ordem[0]["n"] == 5 and (ordem[0]["x0"], ordem[0]["x1"]) == (20, 400)


def test_corta_na_fronteira_quando_o_tesseract_juntou_duas_colunas():
    # vão de só 20 px (< gap) entre a coluna 1 e a 2, cuja borda esquerda é 500
    palavras = [palavra("um", 400, w=30), palavra("texto", 440, w=40), palavra("outro", 505, w=40), palavra("texto", 550, w=40)]
    assert [s["texto"] for s in layout.segmentos(palavras, fronteiras=[500])] == ["um texto", "outro texto"]
    assert len(layout.segmentos(palavras)) == 1


def test_nao_corta_se_uma_palavra_cruza_a_fronteira():
    palavras = [palavra("TITULO", 300, w=300), palavra("GRANDE", 620, w=100)]  # a 1ª vai de 300 a 600, cruzando 500
    assert len(layout.segmentos(palavras, gap=35, fronteiras=[500])) == 1


def test_corta_antes_de_abertura_em_caixa_alta_no_meio_da_linha():
    palavras = [palavra("n.", 0), palavra("19,", 50), palavra("VENDE-SE", 100), palavra("na", 150)]
    abre = lambda anterior, w: w["t"] == "VENDE-SE"
    segs = layout.segmentos(palavras, corta_antes=abre)
    assert [s["texto"] for s in segs] == ["n. 19,", "VENDE-SE na"]
    # os dois pedaços ficam na mesma coluna e na mesma linha do Tesseract, mas não são reunidos
    assert len(layout.atribuir_colunas(segs, [(0, 1000)])) == 2


def linha_de_palavras(n, espaco, h=15, l=1):
    return [palavra("palavra", i * (60 + espaco), h=h, w=60, l=l) for i in range(n)]


def test_espaco_mediano_e_gap_relativo():
    letra_grande = linha_de_palavras(6, 52, h=76)
    assert layout.espaco_mediano(letra_grande) == 52
    assert layout.gap_da_pagina(letra_grande) == 3.5 * 52  # 182: não corta o espaço normal de 52 nem o de 77
    assert layout.gap_da_pagina(linha_de_palavras(6, 9)) == 35  # letra pequena: vale o mínimo
    assert layout.gap_da_pagina([]) == 35


def test_gap_relativo_mantem_a_linha_de_letra_grande_inteira():
    palavras = linha_de_palavras(6, 52, h=76)
    gap = layout.gap_da_pagina(palavras)
    assert len(layout.segmentos(palavras, gap=35)) == 6  # com o gap fixo vira 6 pedaços
    assert len(layout.segmentos(palavras, gap=gap)) == 1


def test_escala_da_letra():
    assert layout.escala_da_letra(linha_de_palavras(5, 10, h=15)) == 1.0
    assert layout.escala_da_letra(linha_de_palavras(5, 10, h=8)) == 1.0  # nunca menor que 1
    assert layout.escala_da_letra(linha_de_palavras(5, 10, h=75)) == 5.0
    assert layout.escala_da_letra([palavra("a", 0, h=90)]) == 1.0  # só palavras com 3 letras ou mais contam


def test_escala_alarga_as_tolerancias_de_borda():
    segs = [seg(100 + (i % 5) * 40, 600, y=20 * i) for i in range(60)]  # x0 espalhado em 160 px
    assert len(layout.bordas_de_colunas(segs, escala=1.0)) > 1
    assert len(layout.bordas_de_colunas(segs, escala=2.0)) == 1
    assert layout.colunas([100, 500], 1000, escala=2.0) == [(0, 440.0), (440.0, 1000)]
