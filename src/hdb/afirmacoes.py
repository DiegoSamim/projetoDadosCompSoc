"""Quadro único de afirmações com veredito (puro; sem banco).

Recebe o resultado de `medidas.calcular` e aplica o critério fixado antes de ver os números:
compara o último período com uma base (o primeiro período com n e n efetivo >= 30, por visão) em três visões
(bruta, só JC e, nos temas, ajustada pela mistura de tipos).
"""
import numpy as np

from hdb.estatistica import fdr_bh
from hdb.relatorio import num, tabela

PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
ULTIMO = PERIODOS[-1]
MIN_N = 30
LIMIAR_DEGRAU = 0.6
SUFIXO_NATUREZA = " (ver natureza)"
DENTRO, MISTURA, TEMA = "dentro do tipo", "mistura da amostra", "tema (acompanha o tipo)"

# (id, texto, natureza, direção esperada: -1 diminui, +1 aumenta, unidade)
AFIRMACOES = (
    (1, "A recompensa nas fugas diminui", DENTRO, -1, "%"),
    (2, "A nação citada nas fugas diminui", DENTRO, -1, "%"),
    (3, "As marcas no corpo nas fugas diminuem", DENTRO, -1, "%"),
    (4, "A idade mediana dos fugidos aumenta", DENTRO, +1, " anos"),
    (5, "A parcela feminina dos aluguéis aumenta", DENTRO, +1, "%"),
    (6, "A fuga perde peso entre os anúncios", MISTURA, -1, "%"),
    (7, "Os temas de fuga perdem peso", TEMA, -1, "%"),
    (8, "O serviço doméstico ganha peso", TEMA, +1, "%"),
    (9, "A ama de leite perde peso", TEMA, -1, "%"),
)


def _nan(x):
    return x is None or (isinstance(x, float) and np.isnan(x))


def _visoes(i):
    return ("bruta", "jc", "ajustada") if i >= 7 else ("bruta", "jc")


def _base(celulas):
    """Primeiro período antes do último com n e n efetivo >= MIN_N; None se não houver."""
    for p in PERIODOS[:-1]:
        c = celulas.get(p) or {}
        if c.get("n", 0) >= MIN_N and c.get("n_ef", 0) >= MIN_N:
            return p
    return None


def _ultimo_ok(celulas):
    c = celulas.get(ULTIMO) or {}
    return c.get("n", 0) >= MIN_N and c.get("n_ef", 0) >= MIN_N


def _forma(celulas, base):
    """'um degrau' se mais de 60% da mudança total ocorre num só passo entre períodos vizinhos."""
    if base is None:
        return "—"
    seq = [celulas[p]["valor"] for p in PERIODOS[PERIODOS.index(base):]]
    if any(_nan(v) for v in seq):
        return "—"
    total = seq[-1] - seq[0]
    if total == 0:
        return "gradual"
    passos = [(b - a) / total for a, b in zip(seq, seq[1:])]
    return "um degrau" if max(passos) > LIMIAR_DEGRAU else "gradual"


def _sinal(x):
    return 0 if _nan(x) or x == 0 else int(np.sign(x))


def _zero(ic):
    """O IC contém zero (ou não existe)."""
    return _nan(ic[1]) or _nan(ic[2]) or ic[1] <= 0 <= ic[2]


def quadro(resultados):
    """Lista de dicts, uma por afirmação, na ordem de AFIRMACOES."""
    pvals = [((resultados.get(i) or {}).get("tendencia", {}).get("bruta") or (float("nan"),))[0] for i, *_ in AFIRMACOES]
    padj = fdr_bh(pvals)
    linhas = []
    for (i, texto, natureza, esperado, unidade), p, pa in zip(AFIRMACOES, pvals, padj):
        r = resultados.get(i) or {}
        visoes = _visoes(i)
        bases = {v: _base(r.get(v) or {}) for v in visoes}
        linha = {"id": i, "texto": texto, "natureza": natureza, "esperado": esperado, "unidade": unidade,
                 "p": p, "p_ajustado": float(pa), "sufixo": i >= 6}
        for v in visoes:
            c = r.get(v) or {}
            b = bases[v]
            linha[f"base_{v}"] = b
            linha[f"valor_base_{v}"] = c[b]["valor"] if b else float("nan")
            linha[f"valor_ultimo_{v}"] = c[ULTIMO]["valor"] if c.get(ULTIMO) else float("nan")
            linha[f"dif_{v}"] = (r.get("dif", {}).get(v, {}).get(b, (float("nan"),) * 3)) if b else (float("nan"),) * 3
            linha[f"n_base_{v}"] = c[b]["n"] if b else 0
            linha[f"n_ultimo_{v}"] = c[ULTIMO]["n"] if c.get(ULTIMO) else 0
        linha["forma"] = _forma(r.get("bruta") or {}, bases["bruta"]) if r else "—"
        linha["veredito"], linha["motivo"] = _veredito(r, visoes, bases, esperado, pa, i)
        linhas.append(linha)
    return linhas


def _veredito(r, visoes, bases, esperado, padj, i):
    if not r:
        return "frágil", "Não há dados para esta medida."
    nomes = {"bruta": "bruta", "jc": "só JC", "ajustada": "ajustada"}
    for v in visoes:
        if bases[v] is None:
            return "frágil", f"Na visão {nomes[v]} nenhum período antes do último tem 30 anúncios (n e n efetivo)."
        if not _ultimo_ok(r.get(v) or {}):
            return "frágil", f"Na visão {nomes[v]} o último período tem menos de 30 anúncios (n ou n efetivo)."
    difs = {v: r["dif"][v][bases[v]] for v in visoes}
    sinais = {v: _sinal(difs[v][0]) for v in visoes}
    if len(set(sinais.values())) > 1 or 0 in sinais.values():
        mudou = [nomes[v] for v in visoes if sinais[v] != sinais["bruta"]] or [nomes[v] for v in visoes if sinais[v] == 0]
        return "não sustentada", f"O sinal da diferença muda ou some na visão {', '.join(mudou)}."
    if _zero(difs["bruta"]):
        return "não sustentada", "Na visão bruta o intervalo da diferença contém zero."
    if sinais["bruta"] != esperado:
        return "não sustentada", "A mudança vai no sentido contrário ao da afirmação."
    if i >= 7 and "ajustada" in visoes and _zero(difs["ajustada"]):
        # tema: se a tendência some ao igualar a mistura de tipos, ela era mistura, não mudança de conteúdo
        return "não sustentada", ("Igualando a mistura de tipos, o intervalo da diferença contém zero: "
                                  "a tendência bruta do tema é, em boa parte, mistura de tipos.")
    fracas = [nomes[v] for v in visoes if _zero(difs[v])]
    if fracas:
        motivo = f"Mesmo sinal em todas as visões, mas o intervalo da diferença contém zero na visão {', '.join(fracas)}."
    elif _nan(padj) or padj >= 0.05:
        motivo = "Mesmo sinal e intervalos sem zero, mas a tendência bruta não passa no teste (p ajustado >= 0,05)."
    else:
        suf = SUFIXO_NATUREZA if i >= 6 else ""
        return "sustentada" + suf, "Tendência bruta com p ajustado < 0,05 e diferença com intervalo sem zero, no mesmo sentido, em todas as visões."
    return "parcial", motivo


def _f(x, c=1):
    return "–" if _nan(x) else num(x, c)


def _dif(d, unid):
    return f"{_f(d[0])} [{_f(d[1])}; {_f(d[2])}]" if not _nan(d[0]) else "–"


def _p(x):
    return "–" if _nan(x) else ("<0,001" if x < 0.001 else num(x, 3))


def _base_txt(l):
    b, j = l["base_bruta"], l["base_jc"]
    if b == j:
        t = b or "nenhuma"
    else:
        t = f"bruta: {b or 'nenhuma'}; só JC: {j or 'nenhuma'}"
    if l["id"] >= 7 and l.get("base_ajustada") not in (b, None):
        t += f"; ajustada: {l['base_ajustada']}"
    return t


def _par(l, v):
    return f"{_f(l[f'valor_base_{v}'])} → {_f(l[f'valor_ultimo_{v}'])}"


def formatar(quadro_):
    """Tabela Markdown do quadro."""
    cab = ("#", "Afirmação", "Natureza", "Base", "Valor base → último (bruta)", "Valor base → último (só JC)",
           "Diferença [IC 95%] (bruta / só JC / ajustada)", "p aj.", "Forma", "Veredito", "Motivo")
    linhas = []
    for l in quadro_:
        difs = [_dif(l["dif_bruta"], l["unidade"]), _dif(l["dif_jc"], l["unidade"])]
        if "dif_ajustada" in l:
            difs.append(_dif(l["dif_ajustada"], l["unidade"]))
        linhas.append((l["id"], l["texto"], l["natureza"], _base_txt(l), _par(l, "bruta"), _par(l, "jc"),
                       " / ".join(difs) + ("" if l["unidade"] == "%" else l["unidade"]), _p(l["p_ajustado"]), l["forma"], f"**{l['veredito']}**", l["motivo"]))
    return tabela(cab, linhas)
