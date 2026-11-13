"""Separa em anúncios os segmentos de uma página já ordenados por coluna (ver `hdb.layout`).

Funções puras. A separação é heurística: título, palavra de abertura ("Vende-se", "Fugio"...) ou um
espaço vertical grande abrem um anúncio novo; a qualidade só se confirma olhando as páginas.
"""
import re
import unicodedata
from itertools import groupby
from statistics import mean, median

from hdb import config
from hdb.layout import FIOS


def _letras(texto):
    return [c for c in texto if c.isalpha()]


def _fracao_maiusculas(texto):
    letras = _letras(texto)
    return sum(c.isupper() for c in letras) / len(letras) if letras else 0.0


def _so_letras(texto):
    """Minúsculas, sem acento, hífen nem pontuação: base da comparação com as palavras de abertura."""
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sem_acento if c.isalpha() and unicodedata.category(c) != "Mn")


def distancia(a, b):
    """Distância de edição (Levenshtein) entre duas strings."""
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        atual = [i]
        for j, cb in enumerate(b, 1):
            atual.append(min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (ca != cb)))
        anterior = atual
    return anterior[-1]


def achar_abertura(texto, aberturas=config.ANUNCIO_ABERTURAS, erros=config.ANUNCIO_ABERTURA_ERROS):
    """A palavra de abertura que o texto começa, tolerando `erros` de OCR na 1ª palavra; None se não há.

    Também tenta a 1ª palavra colada à 2ª ("Vende -se"), que o OCR às vezes separa no hífen.
    """
    palavras = texto.split()[:2]
    if not palavras:
        return None
    candidatas = {_so_letras(palavras[0])}
    if len(palavras) > 1 and len(_so_letras(palavras[1])) <= 3:
        candidatas.add(_so_letras("".join(palavras)))
    melhor = None
    for abertura in aberturas:
        alvo = _so_letras(abertura)
        d = min((distancia(c, alvo) for c in candidatas if len(c) >= 4), default=erros + 1)
        if d <= erros and (melhor is None or d < melhor[0]):
            melhor = (d, abertura)
    return melhor[1] if melhor else None


NUMERACAO = re.compile(r"^[\W_]*\d{1,3}\.?\s+[\W_]*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]")


def achar_numeracao(texto):
    """"N." se o texto começa com a numeração de um aviso ("34. Fugio", "36 Fugio"): 1 a 3 dígitos, ponto
    opcional e uma palavra que começa em maiúscula. "15 de março", "n. 17", "1:000$000" e anos não valem,
    nem endereço de título em caixa alta ("60 RUA DO OUVIDOR").
    """
    return "N." if NUMERACAO.match(texto) and _fracao_maiusculas(texto) < 0.6 else None


def e_secao(texto, secoes=config.ANUNCIO_SECOES, erros=config.ANUNCIO_SECAO_ERROS):
    """O texto inteiro é um título de seção conhecido (ex.: "E S C R A V O S  F U G I D O S ."), com `erros` de OCR."""
    letras = _so_letras(texto)
    return len(letras) >= 5 and any(distancia(letras, _so_letras(s)) <= erros for s in secoes)


def abertura_em_caixa_alta(anterior, palavra):
    """Palavra do OCR (dict) em caixa alta que é palavra de abertura: "VENDE-SE" no meio da linha abre anúncio.

    Não vale depois de outra palavra em caixa alta, que seria um título ("PRETO FUGIDO").
    """
    t = palavra["t"]
    depois_de_caixa_alta = len(_letras(anterior["t"])) >= 2 and _fracao_maiusculas(anterior["t"]) >= 0.8
    return (len(_letras(t)) >= 5 and _fracao_maiusculas(t) >= 0.8 and not depois_de_caixa_alta
            and achar_abertura(t) is not None)


def e_titulo(seg, altura_corpo):
    """Letra grande (>= ANUNCIO_TITULO_ALTURA x o corpo da coluna) ou caixa alta curta, e com cara de texto."""
    texto = seg["texto"]
    letras = _letras(texto)
    if e_secao(texto):  # título de seção vale mesmo com confiança baixa e letras espaçadas
        return True
    if seg["conf"] < config.ANUNCIO_TITULO_CONFIANCA or not texto.lstrip()[:1].isupper() or len(letras) < 3 or len(letras) / len(texto.replace(" ", "")) < config.ANUNCIO_TITULO_LETRAS:
        return False
    grande = seg["h"] >= config.ANUNCIO_TITULO_ALTURA * altura_corpo
    caixa_alta = (_fracao_maiusculas(texto) >= config.ANUNCIO_TITULO_MAIUSCULAS
                  and len(texto.split()) <= config.ANUNCIO_TITULO_PALAVRAS)
    return grande or caixa_alta


def e_cabecalho_ou_rodape(seg, altura):
    """Segmento nos extremos da página que é número ou quase todo em maiúsculas."""
    nas_pontas = seg["y"] < config.CABECALHO * altura or seg["y"] > (1 - config.RODAPE) * altura
    return nas_pontas and (not _letras(seg["texto"]) or _fracao_maiusculas(seg["texto"]) >= config.ANUNCIO_TITULO_MAIUSCULAS)


def e_lixo(seg):
    """Confiança média baixa ou quase sem letras."""
    caracteres = seg["texto"].replace(" ", "")
    return seg["conf"] < config.LIXO_CONFIANCA or len(_letras(caracteres)) < config.LIXO_LETRAS * len(caracteres)


def _passo_de_linha(segs, altura_corpo):
    """Distância vertical normal entre linhas: mediana dos saltos (sem contar os que são quase a mesma linha)."""
    saltos = [b["y"] - a["y"] for a, b in zip(segs, segs[1:]) if b["y"] - a["y"] > 0.5 * altura_corpo]
    return median(saltos) if saltos else altura_corpo * 1.5


def _fecha_paragrafo(seg, seguinte, largura_coluna):
    """Linha curta que acaba em ponto, seguida de linha que começa em maiúscula: fim de um anúncio.

    Nos classificados quase não há espaço entre anúncios; a última linha de cada um é a curta.
    """
    curta = seg["x1"] - seg["x0"] < config.ANUNCIO_LINHA_CURTA * largura_coluna
    return curta and seg["texto"].rstrip().endswith(".") and seguinte["texto"].lstrip()[:1].isupper()


def _dividir_coluna(segs):
    """Grupos de segmentos de uma coluna, um por anúncio, com marcas `titulo` e `abertura` em cada segmento."""
    corpo = median(s["h"] for s in segs)
    largura_coluna = sorted(s["x1"] - s["x0"] for s in segs)[int(0.8 * (len(segs) - 1))]
    passo = _passo_de_linha(segs, corpo)
    grupos, anterior = [], None
    for s in segs:
        titulo = e_titulo(s, corpo)
        abertura = achar_abertura(s["texto"]) or achar_numeracao(s["texto"])
        # uma linha logo depois de título continua o mesmo anúncio, mesmo com abertura ou espaço grande
        # (título de seção não conta: "ESCRAVOS FUGIDOS" fica à parte e o aviso 34 abre o seu próprio anúncio)
        depois_de_titulo = anterior is not None and anterior["titulo"] and not anterior["secao"]
        espaco = anterior is not None and s["y"] - anterior["y"] > config.ANUNCIO_ESPACO_VERTICAL * passo
        fim = anterior is not None and _fecha_paragrafo(anterior, s, largura_coluna)
        novo = anterior is None or (not depois_de_titulo and (titulo or abertura or espaco or fim))
        s = {**s, "titulo": titulo, "abertura": abertura, "secao": e_secao(s["texto"])}
        if novo:
            grupos.append([])
        grupos[-1].append(s)
        anterior = s
    return grupos


def _texto_continuo(linhas):
    """Linhas juntas num texto só; hífen de fim de linha seguido de minúscula junta a palavra partida."""
    texto = ""
    for linha in linhas:
        linha = " ".join(p for p in linha.split() if p not in FIOS)
        if texto.endswith("-") and linha[:1].islower():
            texto = texto[:-1] + linha
        else:
            texto = f"{texto} {linha}" if texto else linha
    return " ".join(texto.split())


def _montar(segs, ordem):
    """O dict do anúncio a partir dos seus segmentos (do 1º ao último, em ordem de leitura)."""
    mantidos = [s for s in segs if s["titulo"] or not e_lixo(s)]
    titulos = [s["texto"] for s in segs if s["titulo"] and s in mantidos]
    n = sum(s["n"] for s in mantidos)
    aberturas = [s["abertura"] for s in segs if s["abertura"]]
    return {
        "ordem": ordem, "coluna": segs[0]["coluna"] + 1,
        "titulo": _texto_continuo(titulos) if titulos else None,
        "abertura": aberturas[0] if aberturas else None,
        "texto_bruto": "\n".join(s["texto"] for s in segs),
        "texto": _texto_continuo([s["texto"] for s in mantidos]),
        "confianca": round(sum(s["conf"] * s["n"] for s in mantidos) / n, 1) if n else 0.0,
        "x0": round(min(s["x0"] for s in segs)), "y0": round(min(s["y0"] for s in segs)),
        "x1": round(max(s["x1"] for s in segs)), "y1": round(max(s["y1"] for s in segs)),
        "n_linhas": len(mantidos), "largo": any(s["largo"] for s in segs),
        "n_palavras": sum(s["n"] for s in segs),
    }


def _anexar_fragmentos(grupos):
    """Anexa ao anúncio anterior (da mesma coluna) os de poucos caracteres sem título nem abertura."""
    saida = []
    for g in grupos:
        curto = sum(len(s["texto"]) for s in g if not e_lixo(s)) < config.ANUNCIO_FRAGMENTO
        sem_marca = not any(s["titulo"] or s["abertura"] for s in g)
        if saida and curto and sem_marca and saida[-1][0]["coluna"] == g[0]["coluna"]:
            saida[-1] += g
        else:
            saida.append(list(g))
    return saida


def separar(segs, altura):
    """(anúncios, descartados) de uma página.

    `segs` vem de `layout.atribuir_colunas` (ordem de leitura). Cada anúncio é um dict com ordem, coluna
    (ambas a partir de 1), titulo, abertura, texto_bruto, texto, confianca, x0, y0, x1, y1, n_linhas, largo e
    n_palavras. `descartados` são os segmentos tirados do texto, com `motivo` "cabecalho" ou "lixo";
    o lixo no meio de um anúncio fica só no `texto_bruto`, não é descartado. Toda palavra da página
    acaba em `n_palavras` de algum anúncio ou num descartado.
    """
    descartados = [{**s, "motivo": "cabecalho"} for s in segs if e_cabecalho_ou_rodape(s, altura)]
    restantes = [s for s in segs if not e_cabecalho_ou_rodape(s, altura)]
    grupos = []
    for _, da_coluna in groupby(restantes, key=lambda s: s["coluna"]):
        grupos += _anexar_fragmentos(_dividir_coluna(list(da_coluna)))
    anuncios = []
    for g in grupos:
        if all(e_lixo(s) and not s["titulo"] for s in g):
            descartados += [{**s, "motivo": "lixo"} for s in g]
        else:
            anuncios.append(_montar(g, len(anuncios) + 1))
    return anuncios, descartados
