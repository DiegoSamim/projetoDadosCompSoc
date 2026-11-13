"""OCR das páginas com o Tesseract: reduz a imagem (em tons de cinza) e lê a página inteira (ou coluna por coluna).

`extrair_texto` é função de topo para rodar num ProcessPoolExecutor, longe do navegador.
"""
import os
import time

import cv2
import numpy as np
import pytesseract

from hdb import config

PSM = {"pagina": 3, "colunas": 4}  # 3: layout automático da página; 4: uma coluna de texto variado


def preparar(caminho, largura, binarizar):
    """Imagem em tons de cinza, reduzida a `largura` px se for maior e, se `binarizar`, binarizada (Otsu)."""
    cinza = cv2.imread(str(caminho), cv2.IMREAD_GRAYSCALE)
    if cinza is None:
        raise ValueError(f"não consegui decodificar a imagem {caminho}")
    if cinza.shape[1] > largura:
        escala = largura / cinza.shape[1]
        cinza = cv2.resize(cinza, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    if not binarizar:
        return cinza
    _, binaria = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binaria


def detectar_colunas(binaria, vale_min=0.01, tinta_max=0.45):
    """Faixas horizontais (x0, x1) de cada coluna de texto de uma imagem binária (tinta = 0).

    Soma a tinta de cada coluna de pixels e corta nos vales largos (`vale_min` da largura) onde há
    pouca tinta (até `tinta_max` da tinta típica). O limite é relativo, e não "zero", porque blocos
    de largura total (avisos, títulos) deixam alguma tinta no vão entre as colunas.
    Sem vale, devolve a imagem toda como 1 coluna.
    """
    largura = binaria.shape[1]
    projecao = (binaria == 0).sum(axis=0).astype(float)
    if projecao.max() == 0:
        return [(0, largura)]
    janela = max(largura // 300, 1)  # suaviza o ruído de pixels isolados
    projecao = np.convolve(projecao, np.ones(janela) / janela, mode="same")
    com_tinta = np.flatnonzero(projecao > 0.05 * projecao.max())
    inicio, fim = com_tinta[0], com_tinta[-1] + 1  # as margens não contam como vale
    tipica = np.median(projecao[inicio:fim])
    vazio = projecao <= tinta_max * tipica
    cortes, atual = [], None
    for x in range(inicio, fim):
        if vazio[x] and atual is None:
            atual = x
        elif not vazio[x] and atual is not None:
            if x - atual >= vale_min * largura:
                cortes.append((atual, x))
            atual = None
    limites = [inicio] + [p for vale in cortes for p in vale] + [fim]
    faixas = list(zip(limites[::2], limites[1::2]))
    estreita = 0.03 * largura  # faixas menores que isso são sujeira, não coluna
    return [(int(a), int(b)) for a, b in faixas if b - a >= estreita] or [(0, largura)]


MARGEM = 10  # px de branco em volta da imagem lida


def _ler(imagem, psm, dx=0):
    """Palavras não vazias da imagem como dicts {t, x, y, w, h, c, b, p, l}, na escala da imagem sem a margem.

    `dx` soma o deslocamento da faixa na imagem inteira (modo "colunas").
    """
    dados = pytesseract.image_to_data(imagem, lang="por", config=f"--psm {psm}",
                                      output_type=pytesseract.Output.DICT)
    zeros = [0] * len(dados["text"])
    esquerda, topo = dados.get("left", zeros), dados.get("top", zeros)
    largura, altura = dados.get("width", zeros), dados.get("height", zeros)
    return [{"t": palavra, "x": int(esquerda[i]) - MARGEM + dx, "y": int(topo[i]) - MARGEM,
             "w": int(largura[i]), "h": int(altura[i]), "c": float(dados["conf"][i]),
             "b": dados["block_num"][i], "p": dados["par_num"][i], "l": dados["line_num"][i]}
            for i, palavra in enumerate(dados["text"]) if palavra.strip()]


def _montar_texto(palavras):
    """Texto com "\n" entre linhas e "\n\n" quando muda o bloco ou o parágrafo do Tesseract."""
    texto, anterior = "", None
    for w in palavras:
        if anterior is None:
            sep = ""
        elif (w["b"], w["p"]) != anterior[:2]:
            sep = "\n\n"
        elif w["l"] != anterior[2]:
            sep = "\n"
        else:
            sep = " "
        texto += sep + w["t"]
        anterior = (w["b"], w["p"], w["l"])
    return texto


def _com_margem(imagem):
    """Margem branca em volta: o Tesseract lê pior texto colado na borda."""
    return cv2.copyMakeBorder(imagem, MARGEM, MARGEM, MARGEM, MARGEM, cv2.BORDER_CONSTANT, value=255)


def _tentar(caminho_imagem, largura):
    """Uma leitura da imagem reduzida a `largura`: {texto, palavras, confiancas, colunas, largura, altura}.

    `colunas` é o nº de blocos do Tesseract (modo "pagina") ou de faixas (modo "colunas");
    `largura` e `altura` são as da imagem lida, a escala das coordenadas das palavras.
    """
    modo = config.OCR_MODO
    cinza = preparar(caminho_imagem, largura, config.OCR_BINARIZAR)
    altura_lida, largura_lida = cinza.shape
    if modo == "pagina":
        palavras = _ler(_com_margem(cinza), PSM[modo])
        colunas, texto = len({w["b"] for w in palavras}), _montar_texto(palavras)
    else:
        # as faixas pedem imagem binária, mas cada coluna é lida do cinza
        binaria = cinza if config.OCR_BINARIZAR else cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        faixas = detectar_colunas(binaria)
        lidas = [_ler(_com_margem(cinza[:, x0:x1]), PSM[modo], dx=x0) for x0, x1 in faixas]
        palavras, colunas = [w for ws in lidas for w in ws], len(faixas)
        texto = "\n\n".join(t for t in map(_montar_texto, lidas) if t)
    return {"texto": texto, "palavras": palavras, "colunas": colunas, "largura": largura_lida,
            "altura": altura_lida, "alvo": largura,
            "confiancas": [w["c"] for w in palavras if w["c"] >= 0]}


def _nome_motor(largura):
    """Identifica a variante da leitura, para coexistir com outras em `textos_ocr`."""
    base = config.OCR_LARGURAS[0]
    variante = "otsu" if config.OCR_BINARIZAR else "cinza"
    sufixo = "" if largura == base else f"-{largura}"
    return (f"tesseract-{pytesseract.get_tesseract_version()} por "
            f"psm{PSM[config.OCR_MODO]}-{config.OCR_MODO}-{variante}{sufixo}")


def _escada(caminho_imagem):
    """Tenta cada largura de `OCR_LARGURAS` até uma render `OCR_MIN_CARACTERES`; senão, a com mais caracteres."""
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")  # um Tesseract por processo, sem disputar CPU
    tentativas = []
    for largura in config.OCR_LARGURAS:
        tentativas.append(_tentar(caminho_imagem, largura))
        if len(tentativas[-1]["texto"]) >= config.OCR_MIN_CARACTERES:
            break
    return max(tentativas, key=lambda t: len(t["texto"]))


def extrair_texto(caminho_imagem):
    """Lê o texto da imagem. Devolve {texto, confianca, colunas, motor, segundos, largura, palavras}.

    A leitura é a de `_escada`. No modo "pagina", `colunas` é o número de blocos do Tesseract.
    `palavras` (formato de `ler_palavras`) deixa segmentar a página sem um 2º OCR.
    """
    inicio = time.monotonic()
    t = _escada(caminho_imagem)
    confiancas = t["confiancas"]
    return {
        "texto": t["texto"],
        "confianca": round(sum(confiancas) / len(confiancas), 1) if confiancas else 0.0,
        "colunas": t["colunas"],
        "motor": _nome_motor(t["alvo"]),
        "segundos": round(time.monotonic() - inicio, 1),
        "largura": t["alvo"],
        "palavras": t["palavras"],
    }


def ler_palavras(caminho_imagem):
    """Palavras da página com posição: {largura, altura, palavras, motor, segundos}.

    Mesma preparação e escada de larguras de `extrair_texto`; as coordenadas são as da imagem lida.
    """
    inicio = time.monotonic()
    t = _escada(caminho_imagem)
    return {"largura": t["largura"], "altura": t["altura"], "palavras": t["palavras"],
            "motor": _nome_motor(t["alvo"]), "segundos": round(time.monotonic() - inicio, 1)}
