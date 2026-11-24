"""Corpus para a modelagem de tópicos: escolhe os anúncios e padroniza o texto (grafia da época -> atual).

Funções puras sobre o texto de OCR. O texto original nunca é alterado: o padronizado vai para outra tabela.
"""
import re
import unicodedata
from collections import Counter

from hdb import config

# --- listas editáveis (tudo em minúsculas e sem acento: é como o texto é comparado) ---

GRAFIA = {  # grafia da época -> atual (palavra inteira); o que é regra geral está em `_regras_gerais`
    "hum": "um", "huma": "uma", "huns": "uns", "humas": "umas", "dous": "dois", "douz": "dois",
    "anno": "ano", "annos": "anos", "fugio": "fugiu", "evadio": "evadiu", "sahio": "saiu", "sahiu": "saiu",
    "sahir": "sair", "sahida": "saida", "camiza": "camisa", "camizas": "camisas", "mez": "mes", "mezes": "meses",
    "hontem": "ontem", "alli": "ali", "ahi": "ai", "dahi": "dai",
}
# Nomes de pessoas (anunciante, vendedor, tesoureiro, ou a própria pessoa anunciada): não dizem sobre o que é o anúncio
# e faziam um tópico só de nomes. O nome da pessoa escravizada anunciada já está no campo `nomes` do banco, então
# todos saem do corpus. Só entram os que aparecem entre as 400 palavras mais frequentes.
NOMES = frozenset("""
jose antonio pedro manoel francisco joao joaquim luiz maria ana bento domingos silva ferreira costa paula
""".split())
# Loteria e comércio: anúncios de bilhete ("comprou por conta da sociedade...") repetem o mesmo formulário
# e atraíam um tópico próprio. "conta" aqui é "por conta de"; "sorte" e "premio" não aparecem entre as mais frequentes.
LOTERIA = frozenset("loteria bilhete bilhetes comprou conta".split())
OCR = {  # erros de OCR frequentes (palavra inteira) -> forma correta; contagens = nº de anúncios no corpus real
    "luga": "aluga",  # 116 anúncios contra 90 de "aluga": o "a" inicial se perde (também "luga-se")
    "recisa": "precisa", "ecisa": "precisa",  # 41 e 7 contra 43 de "precisa": perde o "p" (e o "pr")
    "quizer": "quiser",  # 29: "z" no lugar de "s" (grafia da época misturada ao OCR)
    "ende": "vende", "endem": "vendem",  # 34 e 7: perde o "v"; mesmo padrão de luga/recisa e ao lado de "vende" (132)
    "bum": "um", "buma": "uma",  # 14 e 10: "hum/huma" lidos com "b" (viram vazias)
    "aunos": "anos",  # 9: "annos" com o "nn" lido como "un"
}
VAZIAS = frozenset("""
a o as os um uma uns umas de do da dos das no na nos nas ao aos a pelo pela pelos pelas em por para com sem sob
sobre ate entre desde que quem qual quais cujo cuja se si te me lhe lhes lhe nao e ou mas como quando onde
mais muito muita pouco ja tambem so assim tal tais este esta estes estas esse essa esses essas aquele aquela
aquilo isto isso seu sua seus suas meu minha nosso nossa ele ela eles elas foi era ser sido tem teve tinha
ha houve mesmo mesma der dar dado dirija dirijase dirijam dirigir adverte trata tratar
rua largo beco travessa praia campo casa numero
ras rus ros rea nde des pra pro
""".split()) | NOMES | LOTERIA
ENDERECO = re.compile(  # logradouro + até 45 caracteres + "n. 12" (como em hdb.campos); "n. 12" solto também sai
    r"\b(?:rua|largo|beco|praia|travessa|campo|praca|ladeira)\b[^;.:\n]{0,45}?\bn\b[.,]?\s*[º°o]?\.?\s*\d+"
    r"|\bn\b[.,]?\s*[º°o]?\.?\s*\d+")
DUPLAS = re.compile(r"([bcdfglmnpt])\1")  # consoantes dobradas da época: annos, sabbado, offerece, bella (ss e rr ficam)
LETRAS = re.compile(r"[a-z]+")

MOTIVOS = {
    "tipo": "tipo 'outro' ou sem tipo", "incerto": "aluguel sem marca de escravizado", "confianca": "confiança do OCR baixa ou ausente",
    "curto": "poucas palavras (pedaço de anúncio)",
}


def _sem_acento(texto):
    """Minúsculas e sem acento (ç vira c)."""
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if not unicodedata.combining(c))


def _regras_gerais(palavra):
    """Regras de grafia que valem para qualquer palavra: ph->f, th->t, consoante dobrada -> simples."""
    return DUPLAS.sub(r"\1", palavra.replace("ph", "f").replace("th", "t"))


def _atual(palavra):
    return OCR.get(palavra) or GRAFIA.get(palavra) or GRAFIA.get(_regras_gerais(palavra)) or _regras_gerais(palavra)


def contar_palavras(texto):
    """Número de palavras do texto (separadas por espaço)."""
    return len((texto or "").split())


def motivo_descarte(anuncio):
    """Por que o anúncio fica de fora do corpus ('tipo', 'incerto', 'confianca', 'curto'); None se entra."""
    if anuncio.get("c_tipo") in (None, "outro"):
        return "tipo"
    if anuncio.get("c_tipo") == "aluguel_incerto":
        return "incerto"
    confianca = anuncio.get("confianca")
    if confianca is None or confianca < config.CORPUS_CONFIANCA_MIN:
        return "confianca"
    if contar_palavras(anuncio.get("texto")) < config.CORPUS_PALAVRAS_MIN:
        return "curto"
    return None


def selecionar(anuncio):
    """O anúncio (dict com c_tipo, confianca, texto) entra no corpus?"""
    return motivo_descarte(anuncio) is None


def padronizar(texto):
    """Texto para a modelagem: minúsculas, sem acento, grafia atual, sem números, endereços e palavras vazias."""
    norm = ENDERECO.sub(" ", _sem_acento(texto or ""))
    palavras = (_atual(p) for p in LETRAS.findall(norm))
    return " ".join(p for p in palavras if len(p) > 2 and p not in VAZIAS)


def linha_corpus(anuncio_id, texto_padrao):
    """Linha de `anuncio_corpus`."""
    return {"anuncio_id": anuncio_id, "texto_padrao": texto_padrao, "n_palavras": contar_palavras(texto_padrao)}


def resumir(anuncios):
    """Contagens: selecionados e descartados por motivo, por período legal e por tipo."""
    r = {"total": len(anuncios), "selecionados": 0, "descartados": Counter(), "por_periodo": {}, "por_tipo": {}}
    for a in anuncios:
        motivo = motivo_descarte(a)
        r["selecionados"] += motivo is None
        if motivo:
            r["descartados"][motivo] += 1
        for chave, valor in (("por_periodo", a.get("periodo_legal") or "sem ano"), ("por_tipo", a.get("c_tipo") or "sem tipo")):
            sel_desc = r[chave].setdefault(valor, [0, 0])
            sel_desc[motivo is not None] += 1
    r["descartados"] = dict(r["descartados"])
    return r


def formatar_resumo(r):
    """O resumo de `resumir` em texto para o terminal."""
    def grupo(d):
        return [f"  {k}: {s} selecionados, {x} descartados" for k, (s, x) in sorted(d.items())] or ["  nenhum"]
    motivos = [f"  {MOTIVOS[m]}: {n}" for m, n in sorted(r["descartados"].items(), key=lambda mn: -mn[1])] or ["  nenhum"]
    return "\n".join([f"{r['total']} anúncios com campos: {r['selecionados']} no corpus, "
                      f"{r['total'] - r['selecionados']} descartados",
                      "Descartados por motivo:", *motivos, "Por período legal:", *grupo(r["por_periodo"]),
                      "Por tipo:", *grupo(r["por_tipo"])])


def processar(banco, versao_campos=config.VERSAO_CAMPOS, versao=config.VERSAO_CORPUS, lote=config.LOTE_CORPUS):
    """Padroniza os anúncios selecionados e grava em lotes (regravar a mesma `versao` substitui). Devolve o resumo."""
    anuncios = banco.anuncios_para_corpus(versao_campos)
    linhas = [linha_corpus(a["id"], padronizar(a["texto"])) for a in anuncios if selecionar(a)]
    for i in range(0, len(linhas), lote):
        banco.registrar_corpus(versao, linhas[i:i + lote])
    return resumir(anuncios)
