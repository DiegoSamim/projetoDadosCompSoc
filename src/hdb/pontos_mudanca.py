"""Em que ano cada mudança acontece: ponto de mudança único (um degrau) nas medidas de proporção.

Para cada ano candidato k há duas proporções (antes e depois); fica o k de maior log-verossimilhança binomial.
O IC do ano vem do bootstrap dos anúncios, e o p de um teste de permutação dos anos entre anúncios (estatística = ganho de
log-verossimilhança sobre "sem mudança"). Funções puras (NumPy/pandas). Como em estatistica.py, medem o erro de amostragem
dos anúncios, não o viés da busca. Anos com poucos anúncios (n < MIN_N_ANO) não entram no ajuste.
"""
import numpy as np
import pandas as pd
from scipy.special import xlogy

from hdb.ajustes import n_efetivo, so_jc
from hdb.estatistica import SEMENTE, wilson
from hdb.medidas import REPETICOES, _definicoes

MIN_N_ANO = 20
MAX_ANOS_IC = 8        # IC que cobre mais anos que isto não define ponto
ALFA = 0.05
DATAS_LEGAIS = (1831, 1850, 1871)
# afirmações de proporção que têm série anual: {id: nome}
MEDIDAS = {1: "Recompensa nas fugas", 2: "Nação citada nas fugas", 3: "Marcas no corpo nas fugas",
           5: "Parcela feminina nos aluguéis", 6: "Anúncios que são fuga"}
VISOES = ("bruta", "jc", "ajustada")
SEM_PONTO = "sem ponto definido"
BLOCO = 500


def serie_anual(ano, v, w=None, n_min=MIN_N_ANO):
    """DataFrame por ano: n, n_ef, p (proporção), baixo/alto (Wilson, sobre o n efetivo se ponderado) e ok (n >= n_min)."""
    ano = np.asarray(ano, dtype=int)
    v = np.asarray(v, dtype=float)
    w = np.ones(len(v)) if w is None else np.asarray(w, dtype=float)
    linhas = []
    for a in np.unique(ano):
        m = ano == a
        neff = n_efetivo(w[m])
        p = float(np.average(v[m], weights=w[m]))
        _, lo, hi = wilson(p * neff, neff)
        linhas.append({"ano": int(a), "n": int(m.sum()), "n_ef": neff, "p": p, "baixo": lo, "alto": hi, "ok": int(m.sum()) >= n_min})
    return pd.DataFrame(linhas, columns=["ano", "n", "n_ef", "p", "baixo", "alto", "ok"])


def _ll(k, n):
    """Log-verossimilhança binomial de k em n com a proporção estimada (0 log 0 = 0)."""
    p = np.divide(k, n, out=np.zeros(np.shape(k)), where=np.asarray(n) > 0)
    return xlogy(k, p) + xlogy(n - k, 1 - p)


def _somas(rotulos, x, n_anos):
    """Soma de x por rótulo (linha a linha): (B, n_anos)."""
    b = rotulos.shape[0]
    chave = (rotulos + np.arange(b)[:, None] * n_anos).ravel()
    return np.bincount(chave, weights=x.ravel(), minlength=b * n_anos).reshape(b, n_anos)


def _melhor(rotulos, v, w, n_anos):
    """Para cada linha: (índice do 1º ano depois da mudança, ganho de log-verossimilhança sobre 'sem mudança').

    `rotulos` é (B, N); `v` e `w` são (N,) ou (B, N). Com pesos, usa a contagem efetiva (p ponderado x n efetivo)."""
    v, w = np.broadcast_to(v, rotulos.shape), np.broadcast_to(w, rotulos.shape)
    sw, swv, sw2 = (_somas(rotulos, x, n_anos) for x in (w, w * v, w * w))
    with np.errstate(divide="ignore", invalid="ignore"):
        neff = np.where(sw2 > 0, sw * sw / sw2, 0.0)
        k = np.where(sw > 0, swv / sw, 0.0) * neff
    ck, cn = np.cumsum(k, axis=1), np.cumsum(neff, axis=1)
    tk, tn = ck[:, -1:], cn[:, -1:]
    ll = _ll(ck[:, :-1], cn[:, :-1]) + _ll(tk - ck[:, :-1], tn - cn[:, :-1])
    j = ll.argmax(axis=1)
    return j + 1, ll[np.arange(len(j)), j] - _ll(tk, tn)[:, 0]


def _em_blocos(n_rep, f):
    """Junta f(b) (um array por chamada) em blocos de até BLOCO repetições, para limitar a memória."""
    return np.concatenate([f(min(BLOCO, n_rep - i)) for i in range(0, n_rep, BLOCO)])


def ponto_mudanca(ano, v, w=None, n_min=MIN_N_ANO, rep=REPETICOES, semente=SEMENTE):
    """Ponto de mudança único de uma proporção ao longo dos anos.

    `ano`, `v` (0/1) e `w` (peso; 1 se omitido) têm um valor por anúncio. Devolve um dict com `definido`, `ano` (primeiro ano
    do novo patamar), `baixo`/`alto` (IC 95% do ano), `p` (permutação), `antes`/`depois` (proporções), `cobre` (datas legais
    dentro do IC) e `anos_fora` (anos com n < n_min, fora do ajuste). Sem ponto definido (IC cobre mais de MAX_ANOS_IC anos
    ou p >= 0,05) `ano` ainda traz a melhor estimativa, mas `definido` é False.
    """
    ano = np.asarray(ano, dtype=int)
    v = np.asarray(v, dtype=float)
    w = np.ones(len(v)) if w is None else np.asarray(w, dtype=float)
    ok = w > 0
    ano, v, w = ano[ok], v[ok], w[ok]
    anos, cont = np.unique(ano, return_counts=True)
    fora = [int(a) for a, c in zip(anos, cont) if c < n_min]
    vazio = {"definido": False, "ano": None, "baixo": None, "alto": None, "p": float("nan"), "ganho": float("nan"),
             "antes": float("nan"), "depois": float("nan"), "cobre": [], "anos_fora": fora, "n_anos": 0, "motivo": ""}
    manter = np.isin(ano, anos[cont >= n_min])
    ano, v, w = ano[manter], v[manter], w[manter]
    anos = np.unique(ano)
    if len(anos) < 2:
        return {**vazio, "motivo": "menos de 2 anos com n suficiente"}
    rotulos = np.searchsorted(anos, ano)
    ny, N = len(anos), len(ano)
    j0, g0 = _melhor(rotulos[None, :], v, w, ny)
    j0, g0 = int(j0[0]), float(g0[0])
    esq = rotulos < j0
    antes = float(np.average(v[esq], weights=w[esq]))
    depois = float(np.average(v[~esq], weights=w[~esq]))
    rng = np.random.default_rng(semente)

    def boot(b):   # reamostra anúncios; v e w acompanham o anúncio sorteado
        idx = rng.integers(0, N, size=(b, N))
        return _melhor(rotulos[idx], v[idx], w[idx], ny)[0]
    anos_boot = _em_blocos(rep, boot)
    baixo, alto = (int(anos[int(round(q))]) for q in np.percentile(anos_boot, [2.5, 97.5]))
    rng = np.random.default_rng(semente)

    def perm(b):   # embaralha os anos entre os anúncios
        return _melhor(rotulos[np.argsort(rng.random((b, N)), axis=1)], v, w, ny)[1]
    ganhos = _em_blocos(rep, perm)
    p = float((1 + np.sum(ganhos >= g0 - 1e-12)) / (rep + 1))
    largura = alto - baixo + 1
    cobre = [d for d in DATAS_LEGAIS if baixo <= d <= alto]
    definido = p < ALFA and largura <= MAX_ANOS_IC
    motivo = "" if definido else (f"p = {p:.3f} >= 0.05".replace(".", ",") if p >= ALFA else f"IC cobre {largura} anos (> {MAX_ANOS_IC})")
    return {"definido": definido, "ano": int(anos[j0]), "baixo": baixo, "alto": alto, "p": p, "ganho": g0,
            "antes": antes, "depois": depois, "cobre": cobre, "anos_fora": fora, "n_anos": ny, "motivo": motivo}


def _visoes(base):
    """{visão: DataFrame com ano, v, w}: bruta, só JC e ajustada pela mistura de tipos (peso 0 sai)."""
    d = base.dropna(subset=["ano"]).assign(ano=lambda x: x["ano"].astype(int))
    aj = d.assign(w=d["w_aj"])
    return {"bruta": d.assign(w=1.0), "jc": so_jc(d).assign(w=1.0), "ajustada": aj[aj["w"] > 0]}


def calcular_pontos(df, rep=REPETICOES):
    """{id: {"bruta"|"jc"|"ajustada": ponto (ver ponto_mudanca), "serie": {visão: DataFrame de serie_anual}}} das medidas de MEDIDAS.

    `df` é o resultado de `medidas.carregar` (precisa da coluna `ano`)."""
    definicoes = _definicoes(df)
    saida = {}
    for i in MEDIDAS:
        _, base = definicoes[i]
        r = {"serie": {}}
        for nome, d in _visoes(base).items():
            r[nome] = ponto_mudanca(d["ano"], d["v"], d["w"], rep=rep)
            r["serie"][nome] = serie_anual(d["ano"], d["v"], d["w"])
        saida[i] = r
    return saida


def texto_ponto(ponto, com_ic=False):
    """'1850' (ou '1850 [1848–1852]'); '~1853 [1851–1860] impreciso' se p < 0,05 mas o IC é largo; 'sem ponto' se p >= 0,05."""
    if not ponto:
        return "sem ponto"
    if not ponto.get("definido"):
        if ponto.get("p", 1) >= ALFA:
            return "sem ponto"
        return f"~{ponto['ano']} [{ponto['baixo']}–{ponto['alto']}] impreciso"
    t = str(ponto["ano"])
    return f"{t} [{ponto['baixo']}–{ponto['alto']}]" if com_ic else t
