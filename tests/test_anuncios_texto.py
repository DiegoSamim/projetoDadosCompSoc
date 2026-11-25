import pytest

from hdb import anuncios_texto
from hdb.anuncios_texto import separar_texto
from hdb.banco import BancoMemoria

TRECHO = """'18 Se houver alguma pessoa, ou Senhora de Por-
“tugal, e mesino Estrangeira capaz para tratar do arran-
jo de huma casa de pouca familia ; póde dirigir-se a,
ruá detraz do Hospicjo n. 160, para tratar. das con-
dições e seu ajuste. Na mesma casa comprão-se pesos
, de ferro de huma, e duas arrobas.

Perdas,

19 Perdeo-se no dia 12 do corrente mez , huma
caxorrinha de côr amarela, orelhas hum pouco corta-
das, e pello comprido; quem a achar, e a levar à rua
do. Ouvidor sobrado n. 79, receberá 4000 rã. de al-
viçaras. no

ao Perdeo-se hum cão o y perdigeiro , que res:
ponde ao nome Medor , de
cor de rapé; quem o achar é queira entregar à rua do
Cuvidor n. 95 receberá 4jjsoo.rs. de alviçaras.

Ro q Escravos Fugidos.

a1 No dia 12 do corrente vindo de bordo da Su-
maca Lealdade hum escravo , de Nação Mozambique , de
nome Manoel , oflicial de Capateiro , que reme
"""


def test_versao():
    assert anuncios_texto.VERSAO_ANUNCIOS_TEXTO == "v2t"


def test_separa_numeracao_e_ruido():
    achados = separar_texto(TRECHO, 88.04)
    assert [a["ordem"] for a in achados] == [1, 2, 3, 4]
    assert achados[0]["texto"].startswith("'18 Se houver")
    assert achados[1]["texto"].startswith("19 Perdeo-se")
    assert achados[2]["texto"].startswith("ao Perdeo-se hum cão")  # "ao" é número mal lido
    assert achados[3]["texto"].startswith("a1 No dia 12")
    assert {a["confianca"] for a in achados} == {88.0}


def test_hifenizacao_e_quebras():
    texto = separar_texto(TRECHO)[0]["texto"]
    assert "Portugal" in texto and "arranjo" in texto and "\n" not in texto
    assert "Por-" not in texto


def test_hifen_de_pronome_fica():
    achados = separar_texto("Vende-\nse huma preta de nação Benguella, moça e sadia, na rua do Ouvidor.")
    assert achados[0]["texto"].startswith("Vende-se huma")
    assert achados[0]["abertura"] == "VENDE-SE"


def test_titulos_de_secao():
    achados = separar_texto(TRECHO)
    assert [a["titulo"] for a in achados] == [None, "Perdas", "Perdas", "Escravos Fugidos"]
    assert all("Perdas," not in a["texto"] for a in achados)  # o título não vira anúncio nem texto
    assert not any(a["texto"].startswith("Ro q") for a in achados)


def test_continuacao_anexada():
    texto = ("Fugio hoje da rua do Ouvidor n. 5 hum escravo de nome Joaquim, crioulo, alto e magro.\n\n"
             "quem o levar à mesma casa será generosamente recompensado, pelo seu senhor, de boa fé.")
    achados = separar_texto(texto)
    assert len(achados) == 1
    assert "generosamente" in achados[0]["texto"]
    assert achados[0]["abertura"] == "FUGIO"


@pytest.mark.parametrize("texto", ["", "   \n\n ", None])
def test_pagina_vazia(texto):
    assert separar_texto(texto) == []


def test_sem_aberturas_vira_um_so_anuncio_e_lixo_cai():
    texto = "JORNAL DO COMMERCIO\n\n1828\n\nnotícias do dia sobre o preço do açúcar e do café no mercado do Rio."
    achados = separar_texto(texto)
    assert len(achados) == 1
    assert achados[0]["abertura"] is None
    assert "açúcar" in achados[0]["texto"]
    assert separar_texto("12 345 678\n\n--- . ,") == []


def _banco_com_paginas():
    b = BancoMemoria()
    ids = []
    for i in (1, 2, 3):
        b.registrar_ocorrencia({"bib": "a", "acervo": "A", "termo": "t", "ocorrencia": i, "total_ocorrencias": 3,
                                "ano": "1828", "edicao": "1", "pagina": "1", "pagina_fisica": str(i), "link": "x"})
        p = b.pagina("a", i)
        ids.append(p["id"])
        b.registrar_sucesso(p["id"], "eu", 10, 10, 1, {"texto": TRECHO, "confianca": 80.0, "colunas": 1,
                                                       "motor": "t", "segundos": 1.0}, 1.0, 0)
    return b, ids


def test_banco_paginas_sem_anuncios():
    b, (p1, p2, p3) = _banco_com_paginas()
    assert b.paginas_sem_anuncios("v2") == [p1, p2, p3]
    b.registrar_anuncios(p1, "v2", [{"ordem": 1, "texto": "x"}])
    b.registrar_anuncios(p2, "v2t", [{"ordem": 1, "texto": "y"}])
    assert b.paginas_sem_anuncios("v2") == [p3]
    texto, conf = b.texto_da_pagina(p3)
    assert texto == TRECHO and conf == 80.0
    assert b.texto_da_pagina(999) == (None, None)


def test_banco_anuncios_para_campos_le_v2_e_v2t():
    b, (p1, p2, _) = _banco_com_paginas()
    b.registrar_anuncios(p1, "v2", [{"ordem": 1, "texto": "a", "titulo": None, "abertura": None}])
    assert [a["texto"] for a in b.anuncios_para_campos("v2")] == ["a"]  # sem v2t, igual a antes
    b.registrar_anuncios(p2, "v2t", [{"ordem": 1, "texto": "b"}])
    assert [a["texto"] for a in b.anuncios_para_campos("v2")] == ["a", "b"]
    assert [a["texto"] for a in b.anuncios_para_campos("v2t")] == ["b"]
    assert [a["texto"] for a in b.anuncios_para_campos(("v2",))] == ["a"]
