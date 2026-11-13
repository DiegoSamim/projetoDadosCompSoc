import pytest

from hdb import anuncios


def seg(texto, y, coluna=0, h=15, conf=90.0, x0=100, x1=400, **resto):
    return {"x0": x0, "x1": x1, "y0": y - 7, "y1": y + 7, "y": y, "h": h, "n": len(texto.split()),
            "texto": texto, "conf": conf, "linha": (1, 1, round(y)), "coluna": coluna, "largo": False, **resto}


def corpo(texto, y, **kw):
    return seg(texto, y, **kw)


def separar(segs, altura=1000):
    return anuncios.separar(segs, altura)


def test_distancia_de_edicao():
    assert anuncios.distancia("vende", "vende") == 0
    assert anuncios.distancia("ende", "vende") == 1
    assert anuncios.distancia("abc", "xyz") == 3


@pytest.mark.parametrize("texto, esperado", [
    ("Vende-se uma preta", "VENDE-SE"),
    ("VENDE-SE, na rua", "VENDE-SE"),
    ("Vende se um escravo", "VENDE-SE"),  # o OCR separou no hífen
    ("Vendese um escravo", "VENDE-SE"),
    ("Evadio-se o preto", "EVADIO-SE"),
    ("Fugio o escravo", "FUGIO"),
    ("Fugia ontem", "FUGIO"),  # 1 erro de OCR
    ("ENDE-SE uma casa", "ENDE-SE"),
    ("Desapparecen do rio", "DESAPPARECEU"),
    ("a rua do Ouvidor", None),
    ("Casa para alugar", None),
    ("", None),
])
def test_achar_abertura(texto, esperado):
    assert anuncios.achar_abertura(texto) == esperado


def test_titulo_por_altura_e_por_caixa_alta():
    assert anuncios.e_titulo(seg("Importante leilão", 0, h=36), 15)
    assert anuncios.e_titulo(seg("PRETO FUGIDO.", 0), 15)
    assert not anuncios.e_titulo(seg("um texto qualquer comum", 0), 15)
    assert not anuncios.e_titulo(seg("A B C D E F G H I J", 0), 15)  # caixa alta, mas 10 palavras
    assert not anuncios.e_titulo(seg("1 8 5 0", 0, h=40), 15)  # sem letras
    assert not anuncios.e_titulo(seg("Importante leilão", 0, h=36, conf=30), 15)  # ruído em letra grande


def test_titulo_abre_anuncio_e_vira_titulo():
    segs = [corpo("um texto do anúncio anterior que segue", 100), corpo("segue na linha de baixo do anúncio", 120),
            seg("PRETO FUGIDO.", 140, h=30), corpo("Evadio-se o preto Luiz que andava", 170),
            corpo("na casa do senhor dele", 190)]
    achados, _ = separar(segs)
    assert len(achados) == 2
    assert achados[1]["titulo"] == "PRETO FUGIDO."
    assert achados[1]["abertura"] == "EVADIO-SE"  # a linha logo após o título continua o mesmo anúncio
    assert achados[1]["texto"].startswith("PRETO FUGIDO. Evadio-se")


def test_palavra_de_abertura_separa_anuncios():
    segs = [corpo("Vende-se uma casa grande na rua", 100), corpo("do Ouvidor com quintal e jardim", 120),
            corpo("Aluga-se um sobrado de dois andares", 140), corpo("na rua da Quitanda numero doze", 160)]
    achados, _ = separar(segs)
    assert [a["abertura"] for a in achados] == ["VENDE-SE", "ALUGA-SE"]
    assert [a["ordem"] for a in achados] == [1, 2]


def test_espaco_vertical_separa_anuncios():
    ys = [100, 120, 140, 160, 240, 260, 280]  # o salto de 80 é 4x o passo de 20
    segs = [corpo(f"linha de texto numero {i} do anuncio", y) for i, y in enumerate(ys)]
    achados, _ = separar(segs)
    assert [a["n_linhas"] for a in achados] == [4, 3]


def test_linha_curta_com_ponto_fecha_o_anuncio():
    segs = [corpo("primeira linha longa de um anuncio qualquer", 100), corpo("termina aqui.", 120, x1=200),
            corpo("Outro anuncio comeca com maiuscula e segue", 140), corpo("mais uma linha longa desse anuncio", 160)]
    achados, _ = separar(segs)
    assert len(achados) == 2


def test_fragmento_curto_e_anexado_ao_anterior():
    segs = [corpo(f"linha de texto numero {i} do anuncio", 100 + 20 * i) for i in range(4)] + [corpo("fim de", 240)]
    segs += [corpo(f"linha de texto numero {i} do outro anuncio", 340 + 20 * i) for i in range(3)]
    achados, _ = separar(segs)
    assert len(achados) == 2 and achados[0]["texto"].endswith("fim de")
    assert achados[0]["n_linhas"] == 5


def test_fragmento_com_abertura_ou_titulo_nao_e_anexado():
    segs = [corpo(f"linha de texto numero {i} do anuncio", 100 + 20 * i) for i in range(4)] + [corpo("Fugio", 240)]
    segs += [corpo("linha de texto de outro anuncio", 340), corpo("ainda outra linha de texto aqui", 360)]
    assert len(separar(segs)[0]) == 3


def test_colunas_diferentes_nao_se_misturam():
    segs = [corpo("linha da coluna zero um", 100), corpo("linha da coluna zero dois", 120),
            corpo("linha da coluna um primeira", 100, coluna=1), corpo("linha da coluna um segunda", 120, coluna=1)]
    achados, _ = separar(segs)
    assert [a["coluna"] for a in achados] == [1, 2]


def test_hifen_de_fim_de_linha_junta_com_minuscula():
    assert anuncios._texto_continuo(["um escra-", "vo fugido"]) == "um escravo fugido"
    assert anuncios._texto_continuo(["rua do Rio-", "Branco n. 3"]) == "rua do Rio- Branco n. 3"
    assert anuncios._texto_continuo(["  espaços   demais ", "na  linha"]) == "espaços demais na linha"
    assert anuncios._texto_continuo(["a | b", "|", "c"]) == "a b c"


def test_lixo_sai_do_texto_mas_fica_no_bruto():
    segs = [corpo("Vende-se uma casa grande na rua", 100), seg("~~ ;; ' |", 120), seg("xqz wvk", 140, conf=10.0),
            corpo("do Ouvidor com quintal e jardim", 160)]
    achados, descartados = separar(segs)
    assert len(achados) == 1
    assert achados[0]["texto"] == "Vende-se uma casa grande na rua do Ouvidor com quintal e jardim"
    assert "xqz wvk" in achados[0]["texto_bruto"]
    assert achados[0]["n_palavras"] == sum(s["n"] for s in segs) and descartados == []


def test_anuncio_so_de_lixo_vai_para_os_descartados():
    segs = [seg("xqz wvk", 100, conf=10.0), seg("&& ## @@", 120),
            corpo("Vende-se uma casa grande na rua", 400), corpo("mais uma linha de texto bom", 420)]
    achados, descartados = separar(segs)
    assert len(achados) == 1
    assert {d["motivo"] for d in descartados} == {"lixo"} and len(descartados) == 2


def test_cabecalho_e_rodape_sao_descartados():
    segs = [seg("JORNAL DO COMMERCIO", 10), seg("320", 12, x0=900), corpo("Vende-se uma casa grande na rua", 500),
            corpo("do Ouvidor com quintal e jardim", 520), seg("TYPOGRAPHIA NACIONAL", 990)]
    achados, descartados = separar(segs)
    assert len(achados) == 1 and "JORNAL" not in achados[0]["texto"]
    assert sorted(d["texto"] for d in descartados) == ["320", "JORNAL DO COMMERCIO", "TYPOGRAPHIA NACIONAL"]
    assert all(d["motivo"] == "cabecalho" for d in descartados)


def test_texto_minusculo_no_topo_nao_e_cabecalho():
    achados, descartados = separar([corpo("Vende-se uma casa grande na rua", 10), corpo("do Ouvidor com quintal", 30)])
    assert len(achados) == 1 and descartados == []


def test_campos_do_anuncio():
    a, = separar([corpo("Vende-se uma casa grande", 100, conf=80.0), corpo("na rua do Ouvidor numero um", 120, conf=60.0)])[0]
    assert set(a) >= {"ordem", "coluna", "titulo", "abertura", "texto_bruto", "texto", "confianca", "x0", "y0", "x1",
                      "y1", "n_linhas", "largo"}
    assert a["texto_bruto"] == "Vende-se uma casa grande\nna rua do Ouvidor numero um"
    assert (a["x0"], a["y0"], a["x1"], a["y1"]) == (100, 93, 400, 127)
    assert a["confianca"] == 68.0 and a["n_linhas"] == 2 and a["titulo"] is None and a["largo"] is False


def test_abertura_em_caixa_alta_no_meio_da_linha():
    w = lambda t: {"t": t}
    assert anuncios.abertura_em_caixa_alta(w("19,"), w("VENDE-SE"))
    assert anuncios.abertura_em_caixa_alta(w("|"), w("ÇENDESE,"))  # erro de OCR
    assert not anuncios.abertura_em_caixa_alta(w("PRETO"), w("FUGIDO."))  # título em caixa alta
    assert not anuncios.abertura_em_caixa_alta(w("e"), w("vende-se"))


@pytest.mark.parametrize("texto", ["34. A John Scurr fugirão", "36 Fugio, ha 2 annos", "37. A José Maria", "“17. Quem tiver"])
def test_numeracao_de_aviso(texto):
    assert anuncios.achar_numeracao(texto) == "N."


@pytest.mark.parametrize("texto", [
    "n. 17 na rua", "15 de março de 1821", "1:000$000 de premio", "1850. Maria", "rua do Ouvidor 120 casa",
    "19, na rua da Cadeia", "60 RUA DO OUVIDOR", "", "34.Fugio"])
def test_numeracao_falsos_positivos(texto):
    assert anuncios.achar_numeracao(texto) is None


def test_numeracao_abre_anuncio():
    segs = [corpo("34. Fugirao dous moleques no dia de ontem", 100), corpo("ambos de calcas brancas, quem os achar", 120),
            corpo("35. Na noite do dia 11 desapareceu huma negra", 140), corpo("de nacao Cabinda, saia de zuarte", 160)]
    achados, _ = separar(segs)
    assert [a["abertura"] for a in achados] == ["N.", "N."]


@pytest.mark.parametrize("texto", ["ESCRAVOS FUGIDOS.", "E S C R A V O S  F U G I D O S .", "“EscrAvOS FUCIDOS.", "AVISOS", "Noticias maritimas"])
def test_secoes_conhecidas(texto):
    assert anuncios.e_secao(texto)
    assert anuncios.e_titulo(seg(texto, 0, conf=20.0), 15)  # mesmo com confiança baixa


@pytest.mark.parametrize("texto", ["escravos que fugiram ontem", "Vende-se uma casa", "ana", ""])
def test_nao_e_secao(texto):
    assert not anuncios.e_secao(texto)


def test_titulo_de_secao_fecha_o_anuncio_anterior_e_fica_a_parte():
    segs = [corpo("Sahio a luz o decreto das cortes gerais", 100), corpo("e constituintes da nacao portugueza", 120),
            seg("E S C R A V O S F U G I D O S .", 140, conf=20.0), corpo("34. Fugio hum preto ontem", 160),
            corpo("quem o achar procure o senhor", 180)]
    achados, _ = separar(segs)
    assert len(achados) == 3
    assert "ESCRAVOS" not in achados[0]["texto"].replace(" ", "").upper()
    assert achados[1]["titulo"].startswith("E S C R") and "Fugio" not in achados[1]["texto"]
    assert achados[2]["abertura"] == "N."
