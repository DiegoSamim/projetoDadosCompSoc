"""Separa em anúncios o TEXTO do OCR de uma página, sem imagem nem posições (versão "v2t").

Funções puras. O texto do Tesseract (psm3) vem em ordem de leitura, com parágrafos separados por linha em
branco. Um anúncio começa numa linha com numeração ("18 Se houver..."; o OCR também lê "a1", "'18"),
palavra de abertura ("Vende-se", "Fugio") ou título de seção ("Escravos Fugidos", "Perdas"); o que não
começa nada continua o anúncio anterior. A heurística reaproveita a de `hdb.anuncios`.
"""
import re

from hdb import config
from hdb.anuncios import _fracao_maiusculas, _letras, _so_letras, achar_abertura, achar_numeracao, e_secao

VERSAO_ANUNCIOS_TEXTO = "v2t"

# Seções que o jornal usa e `config.ANUNCIO_SECOES` não tem.
SECOES_EXTRAS = ("PERDAS", "ACHADOS", "ESCRAVOS FUGIDOS", "ESCRAVOS PERDIDOS", "COMPRAS", "VENDAS", "ALUGUEIS",
                 "AVISOS DIVERSOS", "ANNUNCIOS DIVERSOS")
MAX_CARACTERES_SECAO = 40  # título de seção é curto
MIN_LETRAS_ANUNCIO = 25  # menos que isto é cabeçalho, rodapé ou resto de coluna
MIN_FRACAO_LETRAS = 0.5  # fração de letras entre os caracteres que não são espaço

_NUMERO_COM_RUIDO = re.compile(r"^[\W_]*[A-Za-z]\d{1,2}\.?$")  # "a1" (o OCR leu o 21 assim)
_PREFIXO_CURTO = re.compile(r"^[\W_]*[A-Za-z]{1,2}[\W_]*$")  # "ao", "Ro", "q": lixo antes da abertura ou do título
_PRONOMES = {"se", "lhe", "lhes", "me", "te", "o", "a", "os", "as", "lo", "la"}  # "Vende-\nse" mantém o hífen


def _junta_linhas(linhas):
    """Linhas num texto só: hífen de fim de linha junta a palavra partida; as demais quebras viram espaço."""
    texto = ""
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        if texto.endswith("-") and not texto.endswith("--"):
            resto = linha.lstrip("\"'“”‘’`.,;:·• ")
            primeira = re.split(r"\W", resto, maxsplit=1)[0]
            if primeira[:1].islower():
                texto = texto + resto if primeira.lower() in _PRONOMES else texto[:-1] + resto
                continue
        texto = f"{texto} {linha}" if texto else linha
    return " ".join(texto.split())


def _sem_prefixo_curto(texto):
    """O texto sem 1 ou 2 fragmentos curtos de lixo no início ("Ro q Escravos Fugidos"); (resto, quantos tirou)."""
    palavras = texto.split()
    tirados = 0
    while tirados < 2 and len(palavras) - tirados > 1 and _PREFIXO_CURTO.match(palavras[tirados]):
        tirados += 1
    return " ".join(palavras[tirados:]), tirados


def _secao(texto):
    """O título de seção que o texto todo é (sem pontuação final nem lixo antes), ou None."""
    if len(texto) > MAX_CARACTERES_SECAO:
        return None
    resto, _ = _sem_prefixo_curto(texto)
    for candidato in {texto, resto}:
        letras = _so_letras(candidato)
        erros = config.ANUNCIO_SECAO_ERROS if len(letras) >= 12 else 1  # curtas: "Perdeo" não é "Perdas"
        if e_secao(candidato, config.ANUNCIO_SECOES + SECOES_EXTRAS, erros):
            return resto.strip(" .,:;-·'\"“”") or None
    return None


def _comeco(linha):
    """"numeracao", "abertura" ou None: a linha abre um anúncio? Tolera lixo de OCR no lugar do número."""
    if achar_numeracao(linha):
        return "numeracao"
    palavras = linha.split()
    if len(palavras) > 1 and _NUMERO_COM_RUIDO.match(palavras[0]) and palavras[1][:1].isupper():
        return "numeracao"
    if achar_abertura(linha):
        return "abertura"
    resto, tirados = _sem_prefixo_curto(linha)
    if tirados and achar_abertura(resto):  # "ao Perdeo-se hum cão": o "ao" é o número mal lido
        return "numeracao"
    return None


def _cortes_no_meio(linha):
    """Posições, no meio da linha, de palavras de abertura em caixa alta ("... ALUGÃO-SE para o serviço"): nas
    páginas de várias colunas o Tesseract emenda linhas de colunas vizinhas e o anúncio novo começa aí.
    Não vale logo depois de outra palavra em caixa alta (seria um título: "PRETO FUGIDO")."""
    cortes, anterior = [], ""
    for m in re.finditer(r"\S+", linha):
        palavra = m.group()
        letras = _letras(palavra)
        caixa_alta = len(letras) >= 2 and _fracao_maiusculas(palavra) >= 0.8
        if (m.start() > 0 and len(letras) >= 5 and _fracao_maiusculas(palavra) >= 0.8 and achar_abertura(palavra)
                and not (len(_letras(anterior)) >= 2 and _fracao_maiusculas(anterior) >= 0.8)):
            cortes.append(m.start())
        anterior = palavra if caixa_alta else ""
    return cortes


def _e_lixo(texto):
    """Pouca letra (tabela, números, ruído) ou texto curto demais para ser um aviso."""
    caracteres = texto.replace(" ", "")
    letras = _letras(caracteres)
    return len(letras) < MIN_LETRAS_ANUNCIO or len(letras) < MIN_FRACAO_LETRAS * len(caracteres)


def _blocos(texto):
    """Os parágrafos do texto como listas de linhas."""
    blocos, atual = [], []
    for linha in texto.splitlines():
        if linha.strip():
            atual.append(linha)
        elif atual:
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    return blocos


def separar_texto(texto, confianca=None):
    """Anúncios do texto de uma página como [{ordem, texto, titulo, abertura, confianca}] (ordem a partir de 1).

    `confianca` (a da página inteira, ou None) vai igual para todos. Títulos de seção valem como `titulo` dos
    anúncios que vierem depois, até o próximo título; não viram anúncio. Texto vazio ou sem nada que pareça
    anúncio dá lista vazia.
    """
    if not texto or not texto.strip():
        return []
    rascunhos, titulo = [], None  # cada rascunho: {"linhas": [...], "titulo", "abertura"}
    for bloco in _blocos(texto):
        corrido = _junta_linhas(bloco)
        secao = _secao(corrido)
        if secao:
            titulo = secao
            continue
        linhas = [bloco[0]]  # um parágrafo pode trazer vários anúncios: parte nas linhas que abrem um
        for linha in bloco[1:]:
            if _comeco(linha) and _secao(linha) is None:
                linhas.append(linha)
            else:
                linhas[-1] += "\n" + linha
        pedacos = []
        for pedaco in linhas:  # e as linhas que emendam um anúncio novo no meio
            antes = 0
            for corte in _cortes_no_meio(pedaco):
                pedacos.append(pedaco[antes:corte])
                antes = corte
            pedacos.append(pedaco[antes:])
        for pedaco in pedacos:
            comeco = _comeco(pedaco.strip()) if pedaco.strip() else None
            if comeco or not rascunhos:
                resto, _ = _sem_prefixo_curto(pedaco.strip())
                abertura = achar_abertura(pedaco) or achar_abertura(resto)
                rascunhos.append({"linhas": [pedaco], "titulo": titulo, "abertura": abertura})
            else:
                rascunhos[-1]["linhas"].append(pedaco)
    anuncios = []
    for r in rascunhos:
        texto_anuncio = _junta_linhas("\n".join(r["linhas"]).splitlines())
        if _e_lixo(texto_anuncio):
            continue
        anuncios.append({"ordem": len(anuncios) + 1, "texto": texto_anuncio, "titulo": r["titulo"],
                         "abertura": r["abertura"],
                         "confianca": round(confianca, 1) if confianca is not None else None})
    return anuncios
