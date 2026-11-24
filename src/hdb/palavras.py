"""Palavras do OCR (com posição) comprimidas para guardar no banco.

Módulo puro, à parte de `captura` e `banco` para os dois poderem importá-lo sem ciclo.
Formato: JSON compacto da lista `palavras` (chaves t,x,y,w,h,c,b,p,l), em zlib e base64 (~50 KB por página).
"""
import base64
import json
import zlib


def comprimir_palavras(dados):
    """Texto base64 da lista `dados["palavras"]` (JSON compacto + zlib)."""
    bruto = json.dumps(dados["palavras"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(zlib.compress(bruto, 9)).decode("ascii")


def descomprimir_palavras(texto, largura=None, altura=None):
    """Inverso de `comprimir_palavras`: {largura, altura, palavras}."""
    palavras = json.loads(zlib.decompress(base64.b64decode(texto)).decode("utf-8"))
    return {"largura": largura, "altura": altura, "palavras": palavras}
