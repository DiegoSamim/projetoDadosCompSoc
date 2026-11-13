import shutil

import cv2
import numpy as np
import pytest

from hdb import config, ocr


def pagina_sintetica(larguras, vao=40, altura=400):
    """Imagem binária (tinta = 0) com um bloco de linhas de "texto" por coluna, separados por vãos brancos."""
    imagem = np.full((altura, sum(larguras) + vao * (len(larguras) + 1)), 255, dtype=np.uint8)
    x = vao
    for largura in larguras:
        for y in range(20, altura - 20, 20):
            imagem[y:y + 8, x:x + largura] = 0
        x += largura + vao
    return imagem


def test_detecta_duas_colunas():
    colunas = ocr.detectar_colunas(pagina_sintetica([300, 300]))
    assert len(colunas) == 2
    (a0, a1), (b0, b1) = colunas
    assert a0 < a1 < b0 < b1
    assert 330 <= a1 <= 345 and 375 <= b0 <= 385  # cada coluna termina onde o texto termina


def test_detecta_tres_colunas():
    assert len(ocr.detectar_colunas(pagina_sintetica([200, 200, 200]))) == 3


def test_uma_coluna_sem_vale():
    assert len(ocr.detectar_colunas(pagina_sintetica([600]))) == 1


def test_vao_estreito_nao_corta():
    assert len(ocr.detectar_colunas(pagina_sintetica([300, 300], vao=3))) == 1


def test_bloco_de_largura_total_nao_esconde_o_vao():
    imagem = pagina_sintetica([300, 300])
    imagem[300:308, :] = 0  # um título que atravessa as duas colunas, como os avisos do jornal
    assert len(ocr.detectar_colunas(imagem)) == 2


def test_imagem_em_branco_e_uma_coluna():
    assert ocr.detectar_colunas(np.full((100, 200), 255, dtype=np.uint8)) == [(0, 200)]


def imagem_cinza(tmp_path):
    cinza = np.random.default_rng(0).integers(0, 256, (600, 6000), dtype=np.uint8)
    caminho = tmp_path / "x.png"
    cv2.imwrite(str(caminho), cinza)
    return caminho


def test_preparar_reduz_e_mantem_cinza(tmp_path):
    img = ocr.preparar(imagem_cinza(tmp_path), 3000, False)
    assert img.shape[1] == 3000
    assert len(np.unique(img)) > 2


def test_preparar_binariza_se_pedido(tmp_path):
    img = ocr.preparar(imagem_cinza(tmp_path), 3000, True)
    assert img.shape[1] == 3000
    assert set(np.unique(img)) <= {0, 255}


def test_preparar_nao_amplia(tmp_path):
    assert ocr.preparar(imagem_cinza(tmp_path), 9000, False).shape[1] == 6000


def test_preparar_imagem_invalida(tmp_path):
    caminho = tmp_path / "x.jpg"
    caminho.write_bytes(b"isso nao e uma imagem")
    with pytest.raises(ValueError):
        ocr.preparar(caminho, 3000, False)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="binário tesseract não instalado")
def test_extrair_texto_de_imagem_gerada(tmp_path):
    imagem = np.full((300, 1200), 255, dtype=np.uint8)
    for i, linha in enumerate(["Fugio o escravo Joaquim", "crioulo de nacao Benguela"]):
        cv2.putText(imagem, linha, (40, 100 + 100 * i), cv2.FONT_HERSHEY_SIMPLEX, 2, 0, 4)
    caminho = tmp_path / "pagina.png"
    cv2.imwrite(str(caminho), imagem)
    r = ocr.extrair_texto(str(caminho))
    assert "escravo" in r["texto"].lower()
    assert r["colunas"] >= 1 and r["confianca"] > 0
    assert r["motor"].startswith("tesseract-") and r["segundos"] >= 0


def _falso_tesseract(monkeypatch, dados):
    monkeypatch.setattr(ocr.pytesseract, "get_tesseract_version", lambda: "5.3")
    monkeypatch.setattr(ocr.pytesseract, "image_to_data", lambda imagem, **kw: dados)


def imagem_duas_colunas(tmp_path):
    caminho = tmp_path / "pagina.png"
    cv2.imwrite(str(caminho), pagina_sintetica([300, 300]))
    return caminho


# duas linhas no 1º parágrafo, um 2º parágrafo; uma palavra vazia e duas sem confiança
DADOS = {"text": ["Fugio", "o", "", "escravo", "x", "AVISOS", "Vende-se"],
         "conf": ["90", "80", "-1", "70", "-1", "60", "50"],
         "block_num": [1, 1, 1, 1, 1, 2, 2], "par_num": [1, 1, 1, 1, 1, 1, 2],
         "line_num": [1, 1, 1, 2, 2, 1, 1]}


def test_modo_pagina_preserva_blocos_e_paragrafos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OCR_MODO", "pagina")
    _falso_tesseract(monkeypatch, DADOS)
    r = ocr.extrair_texto(imagem_duas_colunas(tmp_path))
    assert r["texto"] == "Fugio o\nescravo x\n\nAVISOS\n\nVende-se"
    assert r["colunas"] == 2  # blocos
    assert r["confianca"] == 70.0
    assert r["motor"] == "tesseract-5.3 por psm3-pagina-cinza"


def test_modo_colunas_le_cada_coluna(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OCR_MODO", "colunas")
    _falso_tesseract(monkeypatch, DADOS)
    r = ocr.extrair_texto(imagem_duas_colunas(tmp_path))
    assert r["colunas"] == 2
    assert r["texto"].count("Fugio o\nescravo x\n\nAVISOS\n\nVende-se") == 2
    assert r["motor"] == "tesseract-5.3 por psm4-colunas-cinza"


def test_motor_otsu(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OCR_BINARIZAR", True)
    _falso_tesseract(monkeypatch, DADOS)
    assert ocr.extrair_texto(imagem_duas_colunas(tmp_path))["motor"] == "tesseract-5.3 por psm3-pagina-otsu"


def escada(monkeypatch, tmp_path, textos):
    """Tesseract falso que devolve um texto por tentativa (uma por largura); anota as larguras usadas."""
    larguras, restantes = [], list(textos)
    monkeypatch.setattr(config, "OCR_MODO", "pagina")
    monkeypatch.setattr(config, "OCR_LARGURAS", (100, 150))
    monkeypatch.setattr(ocr.pytesseract, "get_tesseract_version", lambda: "5.3")

    def image_to_data(imagem, **kw):
        larguras.append(imagem.shape[1] - 20)  # sem a margem
        palavras = restantes.pop(0).split()
        n = len(palavras)
        return {"text": palavras, "conf": ["50"] * n, "block_num": [1] * n, "par_num": [1] * n, "line_num": [1] * n}

    monkeypatch.setattr(ocr.pytesseract, "image_to_data", image_to_data)
    caminho = tmp_path / "p.png"
    cv2.imwrite(str(caminho), np.full((50, 300), 255, dtype=np.uint8))
    return caminho, larguras


def test_escada_usa_a_segunda_largura_se_a_primeira_rende_pouco(tmp_path, monkeypatch):
    caminho, larguras = escada(monkeypatch, tmp_path, ["pouco", "palavra " * 40])
    r = ocr.extrair_texto(caminho)
    assert larguras == [100, 150]
    assert r["largura"] == 150 and r["motor"].endswith("-cinza-150")
    assert len(r["texto"]) >= config.OCR_MIN_CARACTERES


def test_escada_para_na_primeira_que_basta(tmp_path, monkeypatch):
    caminho, larguras = escada(monkeypatch, tmp_path, ["palavra " * 40])
    r = ocr.extrair_texto(caminho)
    assert larguras == [100] and r["largura"] == 100 and r["motor"].endswith("-cinza")


def test_escada_sem_sucesso_devolve_a_com_mais_caracteres(tmp_path, monkeypatch):
    caminho, _ = escada(monkeypatch, tmp_path, ["um texto medio", "curto"])
    r = ocr.extrair_texto(caminho)
    assert r["texto"] == "um texto medio" and r["largura"] == 100 and r["motor"].endswith("-cinza")


def test_ler_palavras_devolve_posicoes_sem_a_margem(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OCR_MODO", "pagina")
    dados = {**DADOS, "left": [10, 60, 0, 10, 0, 10, 10], "top": [30, 30, 0, 50, 0, 90, 130],
             "width": [40, 8, 0, 70, 0, 60, 80], "height": [15, 15, 0, 15, 0, 20, 15]}
    _falso_tesseract(monkeypatch, dados)
    r = ocr.ler_palavras(imagem_duas_colunas(tmp_path))
    assert (r["largura"], r["altura"]) == (720, 400)  # a imagem lida, sem a margem
    assert r["motor"] == "tesseract-5.3 por psm3-pagina-cinza" and r["segundos"] >= 0
    primeira = r["palavras"][0]
    assert primeira == {"t": "Fugio", "x": 0, "y": 20, "w": 40, "h": 15, "c": 90.0, "b": 1, "p": 1, "l": 1}
    assert [w["t"] for w in r["palavras"]] == ["Fugio", "o", "escravo", "x", "AVISOS", "Vende-se"]


def test_extrair_texto_traz_as_palavras_e_o_texto_nao_muda(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OCR_MODO", "pagina")
    _falso_tesseract(monkeypatch, DADOS)
    r = ocr.extrair_texto(imagem_duas_colunas(tmp_path))
    assert r["texto"] == "Fugio o\nescravo x\n\nAVISOS\n\nVende-se"
    assert len(r["palavras"]) == 6
