"""Validação dos campos extraídos por regras (recompensa, nação, idade, sexo, marcas) contra rótulos feitos à mão.

Formato do gold (tests/fixtures/campos_gold.json): lista de {"id", "periodo", "tipo", "texto", "rotulos"}.
`rotulos` de fuga: {"recompensa": bool, "nacoes": [str], "idade": int | [min, max] | null, "marcas": bool,
"sexo": "f" | "m" | "ambos" | "nao_diz"}; de aluguel: {"sexo": ...}. Itens sem `rotulos` são ignorados.
"""
import unicodedata
from collections import defaultdict

import numpy as np
from scipy.stats import fisher_exact

from hdb import campos, categorias
from hdb.estatistica import NAN3, wilson

PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
TOTAL = "TOTAL"
CAMPOS = ("recompensa", "nacao", "marcas", "idade", "idade_acerto", "sexo", "sexo_acerto")
TOLERANCIA_IDADE = 1
TRECHO = 160
QUEDA_MINIMA = 15.0  # pontos percentuais
ALFA = 0.05


def _simples(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower().strip()


def extrair_para_comparar(texto):
    """O que o código extrai, no mesmo formato dos rótulos."""
    c = campos.extrair(texto)
    nacoes = list(dict.fromkeys(_simples(n) for n in (c.get("nacoes") or [])))
    idade = None if c.get("idade_min") is None else (c["idade_min"], c.get("idade_max"))
    return {"recompensa": bool(c.get("recompensa")), "nacoes": nacoes, "idade": idade,
            "marcas": bool(categorias.categorias(texto)["marcas"]), "sexo": c.get("sexo") or "nao_diz"}


def _intervalo_rotulado(idade):
    if idade is None:
        return None
    if isinstance(idade, (list, tuple)):
        return (min(idade), max(idade))
    return (idade, idade)


def _novo():
    return {"vp": 0, "fp": 0, "fn": 0, "vn": 0, "erros": []}


def _contar(c, previsto, real, erro):
    chave = "vp" if previsto and real else "fp" if previsto else "fn" if real else "vn"
    c[chave] += 1
    if chave in ("fp", "fn"):
        c["erros"].append(erro)


def comparar(gold):
    """{campo: {período: {vp, fp, fn, vn, erros}}}, com o período "TOTAL". Itens sem `rotulos` não entram."""
    saida = {campo: defaultdict(_novo) for campo in CAMPOS}

    def contar(campo, periodo, previsto, real, erro):
        for p in (periodo, TOTAL):
            _contar(saida[campo][p], previsto, real, erro)

    for it in gold:
        rot = it.get("rotulos")
        if not rot:
            continue
        per, texto = it["periodo"], it["texto"]
        ext = extrair_para_comparar(texto)

        def erro(rotulo, extraido):
            return {"id": it["id"], "trecho": texto[:TRECHO], "rotulo": rotulo, "extraido": extraido}

        if it.get("tipo") == "fuga":
            contar("recompensa", per, ext["recompensa"], bool(rot.get("recompensa")),
                   erro(rot.get("recompensa"), ext["recompensa"]))
            contar("nacao", per, bool(ext["nacoes"]), bool(rot.get("nacoes")), erro(rot.get("nacoes"), ext["nacoes"]))
            contar("marcas", per, ext["marcas"], bool(rot.get("marcas")), erro(rot.get("marcas"), ext["marcas"]))
            real = _intervalo_rotulado(rot.get("idade"))
            contar("idade", per, ext["idade"] is not None, real is not None, erro(rot.get("idade"), ext["idade"]))
            if real is not None and ext["idade"] is not None:
                certo = real[0] - TOLERANCIA_IDADE <= ext["idade"][0] <= real[1] + TOLERANCIA_IDADE
                for p in (per, TOTAL):
                    c = saida["idade_acerto"][p]
                    if certo:
                        c["vp"] += 1
                    else:
                        c["fp"] += 1
                        c["erros"].append(erro(rot.get("idade"), ext["idade"]))
        rs, es = rot.get("sexo", "nao_diz"), ext["sexo"]
        contar("sexo", per, es in ("f", "m"), rs in ("f", "m"), erro(rs, es))
        if rs in ("f", "m") and es in ("f", "m"):
            for p in (per, TOTAL):
                c = saida["sexo_acerto"][p]
                if rs == es:
                    c["vp"] += 1
                else:
                    c["fp"] += 1
                    c["erros"].append(erro(rs, es))
    return {campo: dict(d) for campo, d in saida.items()}


def metricas(c):
    """{precisao, cobertura, f1, n}; precisão e cobertura vêm com (valor, baixo, alto) de Wilson; nan se o denominador é 0."""
    vp, fp, fn = c["vp"], c["fp"], c["fn"]
    prec = wilson(vp, vp + fp)
    cob = wilson(vp, vp + fn)
    p, r = prec[0], cob[0]
    f1 = 2 * p * r / (p + r) if p == p and r == r and (p + r) > 0 else float("nan")
    if f1 == f1:  # IC do F1: Wilson sobre 2VP / (2VP + FP + FN), a mesma razão
        _, lo, hi = wilson(2 * vp, 2 * vp + fp + fn)
    else:
        lo = hi = float("nan")
    return {"precisao": prec, "cobertura": cob, "f1": (f1, lo, hi), "n": vp + fp + fn + c["vn"]}


def queda_de_cobertura(por_periodo, min_n=20):
    """Compara a cobertura do 1º e do último período com >= min_n positivos rotulados (teste exato de Fisher).

    Devolve (cobertura_primeiro, cobertura_último, queda em pontos, p, sinalizada) ou "sem n".
    Sinalizada: queda > 15 pontos e p < 0,05."""
    ordem = [p for p in PERIODOS if p in por_periodo] + [p for p in por_periodo if p not in PERIODOS and p != TOTAL]
    validos = [p for p in ordem if por_periodo[p]["vp"] + por_periodo[p]["fn"] >= min_n]
    if len(validos) < 2:
        return "sem n"
    a, b = por_periodo[validos[0]], por_periodo[validos[-1]]
    ca, cb = a["vp"] / (a["vp"] + a["fn"]), b["vp"] / (b["vp"] + b["fn"])
    p = float(fisher_exact([[a["vp"], a["fn"]], [b["vp"], b["fn"]]])[1])
    queda = (ca - cb) * 100
    return ca, cb, queda, p, bool(queda > QUEDA_MINIMA and p < ALFA)
