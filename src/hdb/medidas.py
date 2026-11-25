"""As 9 medidas das afirmações: carga do corpus e cálculo por período em três visões (bruta, só JC, ajustada).

`carregar` lê o banco (única parte que o toca); `calcular` é puro (pandas/NumPy). Como em estatistica.py e ajustes.py,
os intervalos medem o erro de amostragem dos anúncios com o modelo de temas fixo, não a instabilidade do LDA.
"""
import numpy as np
import pandas as pd

from hdb.ajustes import diferenca_ponderada_ic, media_ponderada_ic, n_efetivo, pesos_mistura, so_jc
from hdb.categorias import categorias
from hdb.estatistica import SEMENTE, bootstrap_ic, cochran_armitage, diferenca_ic, spearman_tendencia, wilson

PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
MIN_N = 30
REPETICOES = 2000
VISOES = ("bruta", "jc", "ajustada")
IDS = tuple(range(1, 10))
# afirmações cujo valor é uma parcela de tema (têm a visão ajustada)
IDS_TEMA = (7, 8, 9)
__all__ = ["PERIODOS", "MIN_N", "SEMENTE", "REPETICOES", "VISOES", "IDS", "carregar", "calcular"]


def periodo_curto(p):
    """'1850–1871 (Eusébio → ...)' vira '1850–1871'."""
    return p if p.startswith("antes") else p.split(" ")[0]


def _ler_tudo(consulta, bloco=1000):
    linhas, inicio = [], 0
    while True:
        parte = consulta().range(inicio, inicio + bloco - 1).execute().data
        linhas += parte
        if len(parte) < bloco:
            return pd.DataFrame(linhas)
        inicio += bloco


def carregar(banco, config):
    """DataFrame com um anúncio por linha: ano, período curto, bib, campos, texto original e as parcelas de temas
    `p_fuga`, `p_servico`, `p_ama` (NaN onde o anúncio não tem mistura de temas no modelo da rodada)."""
    from hdb.topicos import nomear
    db = banco.cliente
    corpus = pd.DataFrame(banco.anuncios_do_corpus(config.VERSAO_CORPUS))
    corpus = corpus[corpus["texto_padrao"].fillna("").str.strip() != ""][["id", "periodo_legal", "ano"]]
    extra = _ler_tudo(lambda: db.table("anuncios_completos")
                      .select("id,texto,bib,c_tipo,c_sexo,c_idade_min,c_idade_max,c_nacoes,c_recompensa")
                      .in_("versao", list(config.VERSOES_ANUNCIOS)).eq("c_versao", config.VERSAO_CAMPOS)
                      .order("id")).drop_duplicates("id")
    df = corpus.merge(extra, on="id", how="left")
    df["periodo"] = df["periodo_legal"].map(lambda p: periodo_curto(p) if isinstance(p, str) else None)
    df = df[df["periodo"].isin(PERIODOS)].copy()
    modelo = config.VERSAO_TOPICOS
    palavras = _ler_tudo(lambda: db.table("topico_palavras").select("topico,palavra,peso").eq("versao", modelo)
                         .order("topico").order("peso", desc=True))
    dist = _ler_tudo(lambda: db.table("anuncio_topicos").select("anuncio_id,topico,proporcao").eq("versao", modelo)
                     .order("anuncio_id").order("topico"))
    nomes = nomear({t: g.sort_values("peso", ascending=False)["palavra"].head(12) for t, g in palavras.groupby("topico")})
    pivo = dist.pivot(index="anuncio_id", columns="topico", values="proporcao").rename(columns=nomes)

    def soma(predicado):
        cols = [n for n in pivo.columns if predicado(n)]
        return pivo[cols].sum(axis=1) if cols else None   # None = tema ausente neste modelo

    partes = {"p_fuga": soma(lambda n: n.startswith("Fuga")),
              "p_servico": soma(lambda n: n.startswith("Mulheres: lavar") or n.startswith("Aluguel de pretos e moleques")),
              "p_ama": soma(lambda n: n == "Ama de leite")}
    for col, serie in partes.items():
        df[col] = df["id"].map(serie) if serie is not None else np.nan
    return df.reset_index(drop=True)


def _tem(serie):
    return serie.map(lambda v: isinstance(v, (list, tuple, np.ndarray)) and len(v) > 0)


def _marcas(df):
    if "marcas" in df:
        return df["marcas"].astype(bool)
    return df["texto"].map(lambda t: len(categorias(t)["marcas"]) > 0 if isinstance(t, str) else False)


def _definicoes(df):
    """{id: (tipo, DataFrame com periodo, bib, v, w_aj)} das 9 medidas; tipo é prop, mediana ou media."""
    d = df.copy()
    d["w_aj"] = pesos_mistura(d)
    d["idade"] = d[["c_idade_min", "c_idade_max"]].astype(float).mean(axis=1)
    fuga = d[d["c_tipo"] == "fuga"]
    alug = d[(d["c_tipo"] == "aluguel") & d["c_sexo"].isin(["f", "m"])]

    def base(sub, serie):
        b = sub[["periodo", "bib", "w_aj"] + (["ano"] if "ano" in sub else [])].copy()
        b["v"] = serie.astype(float)
        return b.dropna(subset=["v"])

    return {
        1: ("prop", base(fuga, fuga["c_recompensa"].fillna(False).astype(bool))),
        2: ("prop", base(fuga, _tem(fuga["c_nacoes"]))),
        3: ("prop", base(fuga, _marcas(fuga))),
        4: ("mediana", base(fuga, fuga["idade"])),
        5: ("prop", base(alug, alug["c_sexo"] == "f")),
        6: ("prop", base(d, d["c_tipo"] == "fuga")),
        7: ("media", base(d, d["p_fuga"])),
        8: ("media", base(d, d["p_servico"])),
        9: ("media", base(d, d["p_ama"])),
    }


def _estat(tipo):
    return np.median if tipo == "mediana" else np.mean


def _celulas(d, tipo, ponderado):
    f = 1 if tipo == "mediana" else 100
    est = media_ponderada_ic(d["v"], d["w"], d["periodo"], n=REPETICOES) if ponderado and len(d) else {}
    saida = {}
    for p in PERIODOS:
        x = d[d["periodo"] == p]
        v = x["v"].to_numpy(dtype=float)
        n = len(v)
        neff = n_efetivo(x["w"]) if ponderado else float(n)
        if n == 0:
            e = lo = hi = float("nan")
        elif ponderado:
            e, lo, hi = est[p]
        elif tipo == "prop":
            e, lo, hi = wilson(int(v.sum()), n)
        else:
            e, lo, hi = bootstrap_ic(v, _estat(tipo), n=REPETICOES)
        saida[p] = {"n": n, "n_ef": float(neff), "valor": e * f, "baixo": lo * f, "alto": hi * f}
    return saida


def _diferencas(d, tipo, ponderado):
    """{período-base: (diferença, baixo, alto)} do último período menos cada base possível."""
    f = 1 if tipo == "mediana" else 100
    ult = PERIODOS[-1]
    gu = d[d["periodo"] == ult]
    saida = {}
    for b in PERIODOS[:-1]:
        gb = d[d["periodo"] == b]
        if len(gb) == 0 or len(gu) == 0:
            saida[b] = (float("nan"),) * 3
        elif ponderado:
            r = diferenca_ponderada_ic(gb["v"], gb["w"], gu["v"], gu["w"], n=REPETICOES)
            saida[b] = tuple(x * f for x in r)
        else:
            r = diferenca_ic(gb["v"], gu["v"], _estat(tipo), n=REPETICOES)
            saida[b] = tuple(x * f for x in r)
    return saida


def _tendencia(d, tipo):
    """(p, estatística): Cochran–Armitage nas proporções, Spearman anúncio a anúncio nas contínuas."""
    if tipo == "prop":
        com = [p for p in PERIODOS if (d["periodo"] == p).any()]
        ks = [int(d.loc[d["periodo"] == p, "v"].sum()) for p in com]
        ns = [int((d["periodo"] == p).sum()) for p in com]
        z, p = cochran_armitage(ks, ns)
        return (p, z)
    rho, p = spearman_tendencia(d["periodo"].map(PERIODOS.index), d["v"])
    return (p, rho)


def calcular(df):
    """{id: {"bruta"|"jc"|"ajustada": {período: {n, n_ef, valor, baixo, alto}}, "dif": {visão: {base: (d, lo, hi)}},
    "tendencia": {"bruta"|"jc": (p, estatística)}}}. Valores em % (idade em anos). A visão ajustada só existe nos temas."""
    saida = {}
    for i, (tipo, base) in _definicoes(df).items():
        visoes = {"bruta": base.assign(w=1.0), "jc": so_jc(base).assign(w=1.0)}
        if i in IDS_TEMA:
            visoes["ajustada"] = base.assign(w=base["w_aj"])
            visoes["ajustada"] = visoes["ajustada"][visoes["ajustada"]["w"] > 0]
        r = {"dif": {}, "tendencia": {}}
        for nome, d in visoes.items():
            pond = nome == "ajustada"
            r[nome] = _celulas(d, tipo, pond)
            r["dif"][nome] = _diferencas(d, tipo, pond)
            if nome != "ajustada":
                r["tendencia"][nome] = _tendencia(d, tipo)
        saida[i] = r
    return saida
