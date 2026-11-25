"""Categorias contadas por período: qualidades, defeitos e marcas no corpo (ofício e cor já vêm de `hdb.campos`).

Puro (sem banco). As listas valem sobre o texto sem acento e em minúsculas (`hdb.campos._simples`). Cada item é
"canônica|variante|variante" (ou "nome=variante|variante"): a ocorrência de qualquer variante conta como a canônica. A última palavra de cada
variante aceita plural em -s/-es; palavras de 7 letras ou mais aceitam 1 erro de OCR (`hdb.anuncios.distancia`).
Cada termo foi mantido por contagem real no corpus (>= 5 anúncios); ver `scripts/notebooks/gerar_categorias.py`.
"""
import re

from hdb.anuncios import distancia
from hdb.campos import _simples

MIN_LETRAS_OCR = 7  # só palavras com tantas letras toleram 1 erro de OCR
JANELA_NEGACAO = 12  # caracteres antes do termo onde "sem <palavra>" o nega

QUALIDADES = (  # contagem de anúncios do corpus corp3 ao lado de cada termo
    "sem vicios|sem vicio|nao tem vicios|nao tem vicio|nao ter vicios|nao ter vicio|nao tendo vicios|nao tendo vicio"
    "|sem defeito|sem defeitos|nao tem defeito|nao tem defeitos|nao tendo defeito",  # 33+3
    "fiel|fieis",  # 44
    "boa conducta|bons costumes",  # 31+
    "humilde",  # 17
    "carinhosa|carinhoso",  # 59
    "sadia|sadio",  # 42
    "robusta|robusto",  # 37
    "perfeita|perfeito",  # 165
    "habil",  # 6
    "prendada",  # 42
    "intelligente|inteligente",  # 17
    "asseiada|asseiado",  # 7
    "de boa figura|boa figura|bonita figura|bella figura|linda figura",  # 45
    "bonita|bonito",  # 106
    "linda|lindo",  # 46
    "formosa|formoso",  # 14
    "diligente",  # 9
    "perita|perito",  # 19
)
DEFEITOS = (  # a negação ("sem vicios", "nao tem vicios") tira a ocorrência daqui
    "vicios|vicio",  # 13
    "molestias|molestia",  # 8
    "defeito|defeituoso|defeituosa|defeitaoso",  # 13
    "doente|enfermo|enferma|enfermidade",  # 6
    "aleijado|aleijada|coxo|coxa|manco|manca|cego|cega",  # 8
)
_DENTE_DE = r"(?:(?:de|do|da|dos|das|um|hum|todos|os|as|alguns|uns|dous|dois|tres|varios|seus|nos|na|no)\s+){0,3}"
_DINHEIRO = r"(?!\s*(?:de\s+)?(?:\d|\$|dinheiro|ouro|prata|reis|mil\b))(?!\W+(?:s[eo]\w*|abaixo|que|sao|\w*guint\w*)\b)(?!\W*\w{0,2}\W+gu\w)(?!\s*:)"  # "sinal de 20$000" é adiantamento; "signaes seguintes" é só título
MARCAS_CORPO = (  # "marca" sozinha é verbo ("marcar" roupa), por isso só valem as formas abaixo; "~" abre uma regex
    "cicatriz|cicatrizes",  # 18
    "signal=~\\b(?:signa[el]s?|signaes|sigua[eil]s?|sizna[el]s?|sign[sn]es|sinaes|sinais|sinal)\\b" + _DINHEIRO,  # 41, com OCR
    "bexigas|bexiga|bexiguento|bexiguenta|bexigoso|bexigosa|bexigueiro",  # 10
    "falta de dentes|falto de dentes|falta de hum dente|falta de um dente|falta de dente|falta dos dentes|desdentado|desdentada",  # 16
    "dentes=~\\b(?:falta\\w*|falto|sem|quebrad\\w+)\\s+" + _DENTE_DE + "dentes?\\b"  # "sem dentes", "falta de todos os dentes"
    "|\\bdentes?\\s+" + _DENTE_DE + "(?:\\w+\\s+)?(?:quebrad|faltan|falt[ao]|podre|limad|serrad|cahid|estragad|careado)\\w*",
    "ferida|feridas|ferimento|chaga|chagas|ulcera|rotura|quebradura|hernia|lanho",
    "queimadura|queimaduras|queimado|queimada",  # 5
    "orelha=~\\borelh\\w{1,3}(?:\\s+\\w+)?\\s+furad\\w*|\\bfurad\\w*\\s+(?:na|nas|da|das)\\s+orelh",
    "ferro no corpo=~\\b(?:argola|ferros?|gargalheira|golilha)\\b(?:[^a-z]+(?:de|ferro|um|hum|grosso|grande))*[^a-z]+(?:no|ao|do|de|nos|aos)[^a-z]+(?:pescoco|pes?|tornozelos?)\\b",
    "olho=cego|cega|vesgo|vesga|zarolho|zarolha|caolho|torto de hum olho|torto de um olho|torto do olho|olho torto",
    "coxo|manco|aleijado|aleijada",
    "dedo=~\\bdedos?\\b[^.;]{0,25}\\b(?:falt|cortad|aleijad|torto|virad|paralit|quebrad|decepad|mutilad)"
    "|\\b(?:falta\\w*|falto|aleijad\\w+|cortad\\w+|paralit\\w+|faltan\\w+)\\s+(?:(?:de|do|dos|um|hum|o|os)\\s+){0,2}(?:\\w+\\s+)?dedos?\\b",
    "mancha|verruga|belida|pinta",
    "risco no rosto=~\\b(?:risc[oa]s?)\\b(?=[^.;]{0,30}\\b(?:cara|rosto|testa|face)\\b)|\\b(?:cara|rosto|testa|face)\\b[^.;]{0,20}\\briscas?\\b",
    "marca=marca no|marca na|marca de|marca do|marca da|marcas|marcado no|marcado na|marcado com|marcado a ferro|com a marca|com marca"
    "|tem marca|tem a marca|tem huma marca|tem uma marca",
)


def _canonica_e_variantes(item):
    """"a|b|c" -> ("a", [a, b, c]); "nome=b|c" usa um nome que não é variante (ex.: "marca" sozinha é verbo)."""
    nome, _, resto = item.partition("=")
    if not resto:
        nome, resto = item.split("|")[0], item
    if resto.startswith("~"):  # regex sobre o texto sem acento
        return nome, [re.compile(resto[1:])]
    return nome, [v.split() for v in resto.split("|")]


def _bate(token, palavra, ultima):
    """O token é a palavra (com plural se for a última da variante), tolerando 1 erro de OCR se ela é longa."""
    formas = (palavra, palavra + "s", palavra + "es") if ultima else (palavra,)
    if token in formas:
        return True
    return len(palavra) >= MIN_LETRAS_OCR and any(abs(len(token) - len(f)) <= 1 and distancia(token, f) <= 1
                                                   for f in formas)


def _negado(norm, inicio):
    janela = norm[max(0, inicio - JANELA_NEGACAO):inicio]
    return bool(re.search(r"\b(?:sem|nem|nao)\s+(?:\w+\s+)?$|\blivre\s+de\s+$", janela))


def ocorrencias(texto, lista, negacao=True):
    """[(canônica, início, fim)] de cada ocorrência (posições no texto sem acento, que tem o tamanho do original).

    Com `negacao`, ocorrência precedida de "sem"/"nem"/"livre de" nos 12 caracteres anteriores é descartada
    ("sem vícios" não é defeito)."""
    norm = _simples(texto or "")
    tokens = [(m.group(), m.start(), m.end()) for m in re.finditer(r"[a-z]+", norm)]
    achadas = []
    for item in lista:
        canonica, variantes = _canonica_e_variantes(item)
        if variantes and isinstance(variantes[0], re.Pattern):
            for m in variantes[0].finditer(norm):
                if not (negacao and _negado(norm, m.start())):
                    achadas.append((canonica, m.start(), m.end()))
            continue
        for palavras in variantes:
            n = len(palavras)
            for k in range(len(tokens) - n + 1):
                if all(_bate(tokens[k + j][0], p, j == n - 1) for j, p in enumerate(palavras)):
                    inicio, fim = tokens[k][1], tokens[k + n - 1][2]
                    if negacao and _negado(norm, inicio):
                        continue
                    achadas.append((canonica, inicio, fim))
    achadas.sort(key=lambda a: (a[1], -(a[2] - a[1])))
    saida, fim_ant = [], -1
    for a in achadas:  # a variante mais longa vence a que começa no mesmo ponto ou está dentro dela
        if a[1] >= fim_ant:
            saida.append(a)
            fim_ant = a[2]
    return saida


def contar(texto, lista, negacao=True):
    """Ocorrências distintas (canônicas, na ordem em que aparecem) dos termos de `lista` no texto."""
    return list(dict.fromkeys(c for c, _, _ in ocorrencias(texto, lista, negacao)))


def categorias(texto):
    """{"qualidades": [...], "defeitos": [...], "marcas": [...]}; "sem vícios" é qualidade e não defeito."""
    return {"qualidades": contar(texto, QUALIDADES, negacao=False),
            "defeitos": contar(texto, DEFEITOS), "marcas": contar(texto, MARCAS_CORPO)}
