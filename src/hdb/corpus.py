"""Corpus para a modelagem de tópicos: escolhe os anúncios e padroniza o texto (grafia da época -> atual).

Funções puras sobre o texto de OCR. O texto original nunca é alterado: o padronizado vai para outra tabela.
"""
import re
import unicodedata
from collections import Counter

from hdb import config
from hdb.anuncios import distancia
from hdb.campos import ENTRE_VERBOS, NEGOCIO, _sinal_de_pessoa, _simples

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
NAO_TROCAR = frozenset("orador rainha".split())  # palavras reais que a descoberta de OCR tomaria por erro (morador, prainha)
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
    "curto": "poucas palavras (pedaço de anúncio)", "sem_pessoa": "fuga sem pessoa nem marca de escravizado (objeto, animal)",
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


def _tem_pessoa(texto):
    """Há sinal de pessoa no texto (palavra de pessoa, marca de escravizado, idade, nação, corpo ou roupa levada)?

    Usa as mesmas heurísticas de `hdb.campos` (privadas, mas é o único lugar que as define).
    """
    return _sinal_de_pessoa(_simples(texto or ""))


def motivo_descarte(anuncio, incluir_incertos=False):
    """Por que o anúncio fica de fora do corpus ('tipo', 'incerto', 'confianca', 'curto', 'sem_pessoa'); None se entra.

    Com `incluir_incertos`, o 'aluguel_incerto' não é descartado por ser incerto (variante do corpus).
    """
    if anuncio.get("c_tipo") in (None, "outro"):
        return "tipo"
    if anuncio.get("c_tipo") == "aluguel_incerto" and not incluir_incertos:
        return "incerto"
    confianca = anuncio.get("confianca")
    if confianca is None or confianca < config.CORPUS_CONFIANCA_MIN:
        return "confianca"
    if contar_palavras(anuncio.get("texto")) < config.CORPUS_PALAVRAS_MIN:
        return "curto"
    if anuncio.get("c_tipo") == "fuga" and not _tem_pessoa(cortar_colado(anuncio.get("texto"))):
        return "sem_pessoa"
    return None


def selecionar(anuncio, incluir_incertos=False):
    """O anúncio (dict com c_tipo, confianca, texto) entra no corpus?"""
    return motivo_descarte(anuncio, incluir_incertos) is None


def cortar_colado(texto):
    """Fica só com o 1º trecho que tem pessoa, quando o OCR colou anúncios vizinhos; o texto inteiro se nenhum tem.

    Os trechos começam em cada verbo de negócio (NEGOCIO) a ENTRE_VERBOS caracteres ou mais do verbo anterior
    ("vende-se ou aluga-se" não divide). O 1º trecho pode ser de outra coisa ("VENDE-SE um despolpador ... VENDE-SE uma preta").
    """
    texto = texto or ""
    verbos = list(NEGOCIO.finditer(_simples(texto)))  # _simples tem o mesmo tamanho: as posições valem no original
    cortes = [0] + [segundo.start() for primeiro, segundo in zip(verbos, verbos[1:])
                    if segundo.start() - primeiro.end() >= ENTRE_VERBOS] + [len(texto)]
    trechos = [texto[a:b] for a, b in zip(cortes, cortes[1:])]
    return next((t for t in trechos if _tem_pessoa(t)), texto)


def padronizar(texto, ocr_extra=None):
    """Texto para a modelagem: minúsculas, sem acento, grafia atual, sem números, endereços e palavras vazias.

    Corta antes o anúncio colado (`cortar_colado`). `ocr_extra` ({erro: certa}, de `descobrir_ocr`) vale para a forma
    já padronizada e perde para as trocas manuais de OCR.
    """
    norm = ENDERECO.sub(" ", _sem_acento(cortar_colado(texto)))
    ocr_extra = ocr_extra or {}
    palavras = []
    for p in LETRAS.findall(norm):
        atual = _atual(p)
        if p not in OCR:
            atual = ocr_extra.get(atual, atual)
        palavras.append(atual)
    return " ".join(p for p in palavras if len(p) > 2 and p not in VAZIAS)


def descobrir_ocr(textos, min_razao=8, min_letras=4, max_freq_suspeita=20):
    """Descobre erros de OCR: palavra rara W a uma letra de distância de uma palavra V muito mais frequente.

    Frequência = nº de textos em que a palavra aparece. W é suspeita de V se distancia(W, V) == 1, len(W) >= min_letras,
    n_v >= min_razao * n_w e n_w <= max_freq_suspeita (W fora de GRAFIA, OCR e VAZIAS). Vários V: vale o mais frequente,
    salvo se o 2º for >= metade dele (ambíguo: só lista). Devolve {"aplicadas": {W: V},
    "recusadas": [(W, V, n_w, n_v, motivo)]}; motivo 'frequente' (W comum demais), 'ambiguo' (V é o melhor candidato)
    ou 'nao_sistematico' (só se aplica quando W é V sem a 1ª letra, o erro típico do OCR).
    """
    freq = Counter()
    for texto in textos:
        freq.update(set(LETRAS.findall(_sem_acento(texto or ""))))
    # índice por apagamento de uma letra: W e V a distância 1 se um é apagamento do outro, ou se dividem um apagamento
    indice = {}
    for v in freq:
        for i in range(len(v)):
            indice.setdefault(v[:i] + v[i + 1:], set()).add(v)
    conhecidas = set(GRAFIA) | set(OCR) | VAZIAS | NAO_TROCAR
    aplicadas, recusadas = {}, []
    for w, n_w in sorted(freq.items()):
        if len(w) < min_letras or w in conhecidas:
            continue
        vizinhas = set(indice.get(w, ())) | {w[:i] + w[i + 1:] for i in range(len(w))}  # V com uma letra a mais ou a menos
        for i in range(len(w)):
            vizinhas |= indice.get(w[:i] + w[i + 1:], set())  # mesmo tamanho, uma letra trocada
        candidatas = sorted(((freq[v], v) for v in vizinhas if v != w and v in freq and freq[v] >= min_razao * n_w
                             and distancia(w, v) == 1), reverse=True)
        if not candidatas:
            continue
        (n_v, v), segunda = candidatas[0], (candidatas[1][0] if len(candidatas) > 1 else 0)
        if n_w > max_freq_suspeita:
            recusadas.append((w, v, n_w, n_v, "frequente"))
        elif segunda * 2 >= n_v:
            recusadas.append((w, v, n_w, n_v, "ambiguo"))
        elif w != v[1:] or len(v) < min_letras + 2:
            # sem dicionário, "uma letra a mais ou a menos" junta palavras legítimas (alho/alto, alianca/afianca);
            # só se aplica o erro sistemático que se viu no corpus: o OCR perde a 1ª letra (luga, ende, recisa)
            recusadas.append((w, v, n_w, n_v, "nao_sistematico"))
        else:
            aplicadas[w] = v
    return {"aplicadas": aplicadas, "recusadas": recusadas}


def linha_corpus(anuncio_id, texto_padrao):
    """Linha de `anuncio_corpus`."""
    return {"anuncio_id": anuncio_id, "texto_padrao": texto_padrao, "n_palavras": contar_palavras(texto_padrao)}


def resumir(anuncios, incluir_incertos=False):
    """Contagens: selecionados e descartados por motivo, por período legal e por tipo."""
    r = {"total": len(anuncios), "selecionados": 0, "descartados": Counter(), "por_periodo": {}, "por_tipo": {}}
    for a in anuncios:
        motivo = motivo_descarte(a, incluir_incertos)
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
    d = r.get("ocr_descoberto") or {"aplicadas": {}, "recusadas": []}
    ocr = [f"Erros de OCR descobertos: {len(d['aplicadas'])} trocas aplicadas, {len(d['recusadas'])} recusadas",
           *[f"  {w} -> {v}" for w, v in list(d["aplicadas"].items())[:40]]]
    return "\n".join([f"{r['total']} anúncios com campos: {r['selecionados']} no corpus, "
                      f"{r['total'] - r['selecionados']} descartados",
                      "Descartados por motivo:", *motivos, "Por período legal:", *grupo(r["por_periodo"]),
                      "Por tipo:", *grupo(r["por_tipo"]), *ocr])


def processar(banco, versao_campos=config.VERSAO_CAMPOS, versao=config.VERSAO_CORPUS, lote=config.LOTE_CORPUS,
              incluir_incertos=False):
    """Padroniza os anúncios selecionados e grava em lotes (regravar a mesma `versao` substitui:
    quem deixou de ser selecionado sai do corpus). Devolve o resumo.

    Duas passadas: a 1ª padroniza e descobre erros de OCR (`descobrir_ocr`); a 2ª reaplica com as trocas descobertas
    (as manuais de `OCR` ganham). O resumo traz `ocr_descoberto` ({"aplicadas", "recusadas"}).
    """
    anuncios = banco.anuncios_para_corpus(versao_campos)
    selecionados = [a for a in anuncios if selecionar(a, incluir_incertos)]
    ocr = descobrir_ocr([padronizar(a["texto"]) for a in selecionados])
    linhas = [linha_corpus(a["id"], padronizar(a["texto"], ocr["aplicadas"])) for a in selecionados]
    for i in range(0, len(linhas), lote):
        banco.registrar_corpus(versao, linhas[i:i + lote])
    # o upsert não apaga: quem deixou de ser selecionado (regra mais rígida) só sai do corpus se for removido aqui
    velhos = set(banco.ids_do_corpus(versao)) - {l["anuncio_id"] for l in linhas}
    if velhos:
        banco.remover_do_corpus(versao, sorted(velhos))
    return {**resumir(anuncios, incluir_incertos), "ocr_descoberto": ocr}
