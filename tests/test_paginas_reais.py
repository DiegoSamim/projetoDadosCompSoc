"""Regressão com palavras reais do Tesseract (tests/fixtures/palavras_*.json), sem imagem nem OCR."""
import json
from pathlib import Path

import pytest

from hdb import captura

FIXTURES = Path(__file__).parent / "fixtures"
COLUNAS = {"p320": (6, 6), "jc1860": (7, 7), "jc1880": (8, 8), "jc1840": (4, 4),
           "drj339": (1, 2), "drj288": (1, 2), "dfl1507": (2, 3)}
ANUNCIOS_ANTES = {"p320": 169, "jc1860": 143, "jc1880": 220, "jc1840": 65}  # contagens antes do gap relativo e da numeração


@pytest.fixture(scope="module")
def paginas():
    saida = {}
    for nome in COLUNAS:
        dados = json.loads((FIXTURES / f"palavras_{nome}.json").read_text())
        saida[nome] = (dados, captura.segmentar_pagina(dados))
    return saida


@pytest.mark.parametrize("nome", COLUNAS)
def test_numero_de_colunas(paginas, nome):
    minimo, maximo = COLUNAS[nome]
    assert minimo <= len(paginas[nome][1]["faixas"]) <= maximo


@pytest.mark.parametrize("nome", COLUNAS)
def test_nenhuma_palavra_some_em_silencio(paginas, nome):
    dados, r = paginas[nome]
    nos_anuncios = sum(a["n_palavras"] for a in r["anuncios"])
    descartadas = sum(s["n"] for s in r["descartados"])
    assert nos_anuncios + descartadas == len(dados["palavras"])
    assert all(s["motivo"] in ("cabecalho", "lixo") for s in r["descartados"])


@pytest.mark.parametrize("nome", ["p320", "jc1860", "jc1880"])  # o jc1840 tem artigos longos legítimos
def test_nenhum_anuncio_enorme(paginas, nome):
    assert max(len(a["texto"]) for a in paginas[nome][1]["anuncios"]) <= 3000


def test_p320_anuncio_do_preto_fugido_nao_mistura_colunas(paginas):
    anuncios = paginas["p320"][1]["anuncios"]
    do_luiz = [a for a in anuncios if "vadio-se" in a["texto"]]
    assert do_luiz and all("Castiçaes" not in a["texto"] for a in do_luiz)
    assert any(a["titulo"] and "PRETO FUGIDO" in a["titulo"] for a in anuncios)
    assert any(a["abertura"] == "EVADIO-SE" for a in anuncios)


def test_p320_reconhece_aberturas(paginas):
    anuncios = paginas["p320"][1]["anuncios"]
    assert sum(1 for a in anuncios if a["abertura"]) >= 20


def test_anuncios_vem_em_ordem_de_leitura(paginas):
    for _, r in paginas.values():
        pares = [(a["coluna"], a["ordem"]) for a in r["anuncios"]]
        assert pares == sorted(pares) and [a["ordem"] for a in r["anuncios"]] == list(range(1, len(pares) + 1))


def _largura_em_colunas(a, r):
    tipica = sorted(x1 - x0 for x0, x1 in r["faixas"])[len(r["faixas"]) // 2]
    return (a["x1"] - a["x0"]) / tipica


def test_p320_preto_fugido_termina_na_rua_do_portao_sem_a_coluna_vizinha(paginas):
    anuncios = paginas["p320"][1]["anuncios"]
    a, = [a for a in anuncios if a["titulo"] and "PRETO FUGIDO" in a["titulo"]]
    assert a["texto"].rstrip().endswith("portão de ferro n.") or "portão de ferro n" in a["texto"][-40:]
    assert "PRECISA" not in a["texto"] and "Magé" not in a["texto"]
    assert not a["largo"] and _largura_em_colunas(a, paginas["p320"][1]) <= 1.25
    seguinte = anuncios[a["ordem"]]  # o anúncio de baixo, "VENDE-SE, na villa de Magé"
    assert "Magé" in seguinte["texto"] and seguinte["abertura"] == "VENDE-SE"


@pytest.mark.parametrize("comeco", ["vende-se uma ama de leite", "aluga-se um preto"])
def test_p320_classificados_de_interesse_nao_cruzam_colunas(paginas, comeco):
    r = paginas["p320"][1]
    achados = [a for a in r["anuncios"] if a["texto"].lower().startswith(comeco)]
    assert achados
    assert all(not a["largo"] or _largura_em_colunas(a, r) <= 1.25 for a in achados)


def test_poucos_anuncios_largos(paginas):
    assert sum(a["largo"] for a in paginas["p320"][1]["anuncios"]) < 8
    assert sum(a["largo"] for a in paginas["jc1860"][1]["anuncios"]) < 4


@pytest.mark.parametrize("nome", ANUNCIOS_ANTES)
def test_contagem_de_anuncios_dos_jornais_antigos_quase_nao_muda(paginas, nome):
    antes = ANUNCIOS_ANTES[nome]
    assert abs(len(paginas[nome][1]["anuncios"]) - antes) <= 0.05 * antes


def _com(r, trecho):
    return [a for a in r["anuncios"] if trecho in a["texto"]]


def test_drj339_pagina_de_uma_coluna_de_letra_grande(paginas):
    r = paginas["drj339"][1]
    anuncios = r["anuncios"]
    assert sum(a["largo"] for a in anuncios) <= 0.1 * len(anuncios)
    aviso35, = _com(r, "John Scurr")
    assert "Cabindas" in aviso35["texto"] and "boçal" not in aviso35["texto"]
    aviso36, = _com(r, "36 Fugio")
    assert "José Maria da Silva" not in aviso36["texto"]
    assert sum(1 for a in anuncios if a["abertura"] == "N.") >= 4


def test_drj339_titulo_de_secao_fecha_o_decreto(paginas):
    r = paginas["drj339"][1]
    com_titulo = [a for a in r["anuncios"] if a["titulo"] and "FUCIDOS" in a["titulo"].upper().replace("G", "C")]
    assert com_titulo
    decreto, = _com(r, "Sahio")
    assert "FUCIDOS" not in decreto["texto"].upper() and "FUGIDOS" not in decreto["texto"].upper()
    assert "Scurr" not in com_titulo[0]["texto"]  # o aviso 34 abre o seu próprio anúncio


def test_drj288_tambem_uma_coluna_sem_largos(paginas):
    anuncios = paginas["drj288"][1]["anuncios"]
    assert sum(a["largo"] for a in anuncios) <= 0.1 * len(anuncios)
