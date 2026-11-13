"""Leitura por colunas: transforma as palavras do OCR em segmentos de linha ordenados coluna a coluna.

Funções puras sobre a lista de palavras ({t, x, y, w, h, c, b, p, l}), sem imagem nem Tesseract.
O Tesseract (psm 3) junta linhas de colunas vizinhas numa só; cortar cada linha nos espaços grandes
devolve um segmento por coluna.
"""
from collections import defaultdict
from statistics import mean, median

from hdb import config

FIOS = {"|", "¦", "│", "||", "|]", "[|", "]|", "!|", "|!"}  # leituras do fio vertical que separa colunas


def _segmento(palavras, parte=0):
    confs = [w["c"] for w in palavras if w["c"] >= 0]
    return {"x0": min(w["x"] for w in palavras), "x1": max(w["x"] + w["w"] for w in palavras),
            "y0": min(w["y"] for w in palavras), "y1": max(w["y"] + w["h"] for w in palavras),
            "y": mean(w["y"] + w["h"] / 2 for w in palavras), "h": median(w["h"] for w in palavras),
            "n": len(palavras), "texto": " ".join(w["t"] for w in palavras),
            "conf": mean(confs) if confs else 0.0, "linha": (palavras[0]["b"], palavras[0]["p"], palavras[0]["l"], parte)}


def espaco_mediano(palavras):
    """Mediana do espaço entre palavras vizinhas da mesma linha do Tesseract; 0 se não há par."""
    linhas = defaultdict(list)
    for w in palavras:
        linhas[(w["b"], w["p"], w["l"])].append(w)
    espacos = []
    for ws in linhas.values():
        ws.sort(key=lambda w: w["x"])
        espacos += [b["x"] - (a["x"] + a["w"]) for a, b in zip(ws, ws[1:]) if b["x"] >= a["x"] + a["w"]]
    return median(espacos) if espacos else 0


def escala_da_letra(palavras):
    """Altura mediana das palavras com 3 letras ou mais / `LAYOUT_LETRA_REF`, no mínimo 1."""
    alturas = [w["h"] for w in palavras if sum(c.isalpha() for c in w["t"]) >= 3]
    return max(1.0, median(alturas) / config.LAYOUT_LETRA_REF) if alturas else 1.0


def gap_da_pagina(palavras):
    """Espaço de corte da página: `LAYOUT_GAP`, ou mais se o espaço normal entre palavras for grande (letra grande)."""
    return max(config.LAYOUT_GAP, config.LAYOUT_GAP_REL * espaco_mediano(palavras))


def _cortar_nas_fronteiras(ws, fronteiras, escala=1.0):
    """Pedaços de um segmento (palavras por x) cortados antes da 1ª palavra que começa à direita de cada fronteira.

    Não corta numa fronteira se alguma palavra a cruza com folga: é título ou figura de verdade.
    """
    pedacos = [ws]
    for f in fronteiras:
        novos = []
        for p in pedacos:
            cruza_m, tol = config.LAYOUT_CRUZA * escala, config.LAYOUT_TOL_BORDA * escala
            cruza = any(w["x"] < f - cruza_m and w["x"] + w["w"] > f + cruza_m for w in p)
            depois = [i for i, w in enumerate(p) if w["x"] >= f - tol]
            if cruza or not depois or depois[0] == 0:
                novos.append(p)
            else:
                novos += [p[:depois[0]], p[depois[0]:]]
        pedacos = novos
    return pedacos


def segmentos(palavras, gap=config.LAYOUT_GAP, fronteiras=(), corta_antes=None, escala=1.0):
    """Segmentos {x0, x1, y0, y1, y, h, n, texto, conf, linha}: as linhas do Tesseract cortadas nos espaços >= gap.

    Com `fronteiras` (bordas esquerdas das colunas 2, 3...), também corta onde um segmento as atravessa.
    `escala` (da letra) alarga as tolerâncias em px. `corta_antes(anterior, palavra)` verdadeiro corta a linha antes dessa palavra (início de anúncio no meio da linha).
    """
    linhas = defaultdict(list)
    for w in palavras:
        linhas[(w["b"], w["p"], w["l"])].append(w)
    saida = []
    for ws in linhas.values():
        ws.sort(key=lambda w: w["x"])
        atual, grupos, parte = [ws[0]], [], 0
        for anterior, w in zip(ws, ws[1:]):
            # o fio vertical entre colunas vira uma "palavra" "|" que fecha o vão; o corte vem depois dela
            abre = bool(corta_antes and corta_antes(anterior, w))
            if w["x"] - (anterior["x"] + anterior["w"]) >= gap or anterior["t"] in FIOS or abre:
                grupos.append((atual, parte))
                atual = []
                parte += abre  # um início de anúncio não pode ser reunido ao pedaço da frente
            atual.append(w)
        grupos.append((atual, parte))
        for g, parte in grupos:
            saida += [_segmento(p, parte) for p in _cortar_nas_fronteiras(g, fronteiras, escala)]
    return saida


def _agrupar(xs, tol):
    """Grupos de valores ordenados em que cada um está a até `tol` do anterior."""
    grupos = []
    for x in sorted(xs):
        if grupos and x - grupos[-1][-1] <= tol:
            grupos[-1].append(x)
        else:
            grupos.append([x])
    return grupos


def bordas_de_colunas(segs, escala=1.0, apoio_min=config.LAYOUT_APOIO_MIN, apoio_rel=config.LAYOUT_APOIO_REL):
    """Bordas esquerdas (x) das colunas: o x0 mais comum entre os segmentos largos.

    As tolerâncias em px crescem com `escala`. Fica o grupo com apoio >= `apoio_rel` x a mediana do apoio dos grupos com apoio >= `apoio_min`.
    """
    largura_min = config.LAYOUT_LARGURA_BORDA * escala
    grupos = _agrupar([s["x0"] for s in segs if s["x1"] - s["x0"] >= largura_min], config.LAYOUT_TOL_BORDA * escala)
    fortes = [len(g) for g in grupos if len(g) >= apoio_min]
    if not fortes:
        return []
    corte = apoio_rel * median(fortes)
    return [round(median(g)) for g in grupos if len(g) >= max(apoio_min, corte)]


def colunas(bordas, largura, escala=1.0):
    """Faixas [x0, x1) das colunas. O corte fica `LAYOUT_TOL_BORDA` à esquerda da borda, para o recuo
    dos parágrafos não passar o segmento para a coluna vizinha; a 1ª faixa começa em 0 e a última acaba em `largura`.
    """
    if not bordas:
        return [(0, largura)]
    cortes = [0] + [b - config.LAYOUT_TOL_BORDA * escala for b in sorted(bordas)[1:]] + [largura]
    return list(zip(cortes, cortes[1:]))


def _indice_da_faixa(x, faixas):
    for i, (_, x1) in enumerate(faixas):
        if x < x1:
            return i
    return len(faixas) - 1


def _juntar(a, b):
    """Junta dois segmentos da mesma linha do Tesseract e da mesma coluna."""
    n = a["n"] + b["n"]
    return {**a, "x1": max(a["x1"], b["x1"]), "y0": min(a["y0"], b["y0"]), "y1": max(a["y1"], b["y1"]),
            "y": (a["y"] * a["n"] + b["y"] * b["n"]) / n, "h": max(a["h"], b["h"]), "n": n,
            "texto": a["texto"] + " " + b["texto"], "conf": (a["conf"] * a["n"] + b["conf"] * b["n"]) / n}


def atribuir_colunas(segs, faixas, largo=config.LAYOUT_LARGO):
    """Segmentos com `coluna` (0 = a da esquerda) e `largo`, na ordem de leitura.

    O segmento vai para a faixa do seu centro; o largo (>= `largo` x a faixa típica, como um título que
    cruza colunas) vai para a faixa onde começa, e entra na ordem vertical dessa coluna.
    Pedaços da mesma linha do Tesseract que caem na mesma coluna são reunidos.
    """
    tipica = median(x1 - x0 for x0, x1 in faixas)
    saida = []
    for s in segs:
        e_largo = s["x1"] - s["x0"] >= largo * tipica
        ref = s["x0"] if e_largo else (s["x0"] + s["x1"]) / 2
        saida.append({**s, "coluna": _indice_da_faixa(ref, faixas), "largo": e_largo})
    saida.sort(key=lambda s: (s["coluna"], s["linha"], s["x0"]))
    juntos = []
    for s in saida:
        anterior = juntos[-1] if juntos else None
        if anterior and (anterior["coluna"], anterior["linha"]) == (s["coluna"], s["linha"]):
            juntos[-1] = {**_juntar(anterior, s), "largo": anterior["largo"] or s["largo"]}
        else:
            juntos.append(s)
    return sorted(juntos, key=lambda s: (s["coluna"], s["y"]))


def ler_em_colunas(palavras, largura, corta_antes=None):
    """(segmentos na ordem de leitura, faixas das colunas, bordas) de uma página."""
    gap, escala = gap_da_pagina(palavras), escala_da_letra(palavras)
    bordas = bordas_de_colunas(segmentos(palavras, gap, corta_antes=corta_antes, escala=escala), escala)
    # 2º passo: com as colunas conhecidas, corta o que o Tesseract ainda juntou por cima da fronteira
    segs = segmentos(palavras, gap, sorted(bordas)[1:], corta_antes, escala)
    faixas = colunas(bordas, largura, escala)
    return atribuir_colunas(segs, faixas), faixas, bordas
