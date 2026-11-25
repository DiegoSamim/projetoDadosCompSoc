"""Anúncios repetidos: o mesmo anúncio publicado várias vezes, detectado por similaridade de texto.

Não há data completa: dois anúncios só são comparados se têm o mesmo `bib`, o mesmo `ano` e edições a no máximo
`JANELA_EDICOES` de distância (edições consecutivas ≈ dias). Similaridade = Jaccard dos conjuntos de shingles de
5 palavras do texto normalizado. Os candidatos vêm de MinHash + bandas LSH (determinístico); a similaridade final
de cada par candidato é o Jaccard exato. Módulo puro (pandas/NumPy), não toca o banco.
"""
import re
import unicodedata
import zlib

import numpy as np
import pandas as pd

JANELA_EDICOES = 30
LIMIAR = 0.6   # provisório: o revisor fixa depois com conferência manual
SIMILARIDADE_MIN = 0.3
TAM_SHINGLE = 5
MIN_PALAVRAS = 8
N_PERM = 64
LINHAS_BANDA = 2   # 32 bandas de 2 linhas: ~95% de recall em similaridade 0.3
_PRIMO = 4294967311
_ORDEM = ["ano", "edicao", "pagina_fisica", "ordem"]
__all__ = ["JANELA_EDICOES", "LIMIAR", "normalizar", "shingles", "pares_candidatos", "agrupar", "resumo"]


def normalizar(texto):
    """Minúsculas, sem acento, sem pontuação, sem números soltos; espaços colapsados."""
    if not isinstance(texto, str):
        return ""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\b\d+\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def shingles(texto):
    """Conjunto de shingles de 5 palavras; vazio se o texto tem menos de 8 palavras normalizadas."""
    p = normalizar(texto).split()
    if len(p) < MIN_PALAVRAS:
        return set()
    return {" ".join(p[i:i + TAM_SHINGLE]) for i in range(len(p) - TAM_SHINGLE + 1)}


def _assinatura(conj, a, b):
    h = np.fromiter((zlib.crc32(s.encode()) for s in sorted(conj)), dtype=np.uint64, count=len(conj))
    return ((h[:, None] * a[None, :] + b[None, :]) % np.uint64(_PRIMO)).min(axis=0)


def _numerico(serie):
    return pd.to_numeric(serie, errors="coerce")


def pares_candidatos(df, similaridade_min=SIMILARIDADE_MIN):
    """DataFrame (id_a, id_b, similaridade, dist_edicao, mesmo_ano_edicao) dos pares na janela com Jaccard exato
    ≥ `similaridade_min`. `id_a` vem antes de `id_b` na ordem (ano, edição, página, ordem)."""
    colunas = ["id_a", "id_b", "similaridade", "dist_edicao", "mesmo_ano_edicao"]
    d = df.copy()
    d["_ed"] = _numerico(d["edicao"])
    d["_ano"] = _numerico(d["ano"])
    for c in ("pagina_fisica", "ordem"):
        d[c] = _numerico(d[c]) if c in d else 0
    d["_sh"] = d["texto"].map(shingles)
    d = d[(d["_sh"].map(len) > 0) & d["_ed"].notna() & d["_ano"].notna() & d["bib"].notna()]
    d = d.sort_values(["bib", "_ano", "_ed", "pagina_fisica", "ordem", "id"], kind="mergesort")
    rng = np.random.RandomState(12345)
    a = rng.randint(1, 2 ** 31 - 1, N_PERM).astype(np.uint64)
    b = rng.randint(0, 2 ** 31 - 1, N_PERM).astype(np.uint64)
    saida = []
    for _, g in d.groupby(["bib", "_ano"], sort=True):
        ids, eds, shs = g["id"].tolist(), g["_ed"].tolist(), g["_sh"].tolist()
        assin = [_assinatura(s, a, b) for s in shs]
        baldes = {}
        for i, sig in enumerate(assin):
            for k in range(N_PERM // LINHAS_BANDA):
                chave = (k, *sig[k * LINHAS_BANDA:(k + 1) * LINHAS_BANDA].tolist())
                baldes.setdefault(chave, []).append(i)
        vistos = set()
        for membros in baldes.values():
            n = len(membros)
            for x in range(n):
                i = membros[x]
                for y in range(x + 1, n):
                    j = membros[y]   # membros em ordem crescente de i (= ordem de edição)
                    if eds[j] - eds[i] > JANELA_EDICOES:
                        break
                    if (i, j) in vistos:
                        continue
                    vistos.add((i, j))
                    inter = len(shs[i] & shs[j])
                    sim = inter / (len(shs[i]) + len(shs[j]) - inter)
                    if sim >= similaridade_min:
                        saida.append((ids[i], ids[j], sim, int(eds[j] - eds[i]), True))
    if not saida:
        return pd.DataFrame(columns=colunas)
    return pd.DataFrame(saida, columns=colunas).sort_values(["id_a", "id_b"]).reset_index(drop=True)


def agrupar(df, limiar=LIMIAR):
    """Devolve o df com `grupo` (id do grupo; sem repetido, grupo próprio) e `representante` (bool: o de menor
    (ano, edição, página, ordem) do grupo). Grupos = componentes conexos dos pares com similaridade ≥ limiar."""
    d = df.reset_index(drop=True).copy()
    pos = {i: k for k, i in enumerate(d["id"])}
    pai = list(range(len(d)))

    def raiz(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    pares = pares_candidatos(d, limiar)
    for r in pares[pares["similaridade"] >= limiar].itertuples():
        ra, rb = raiz(pos[r.id_a]), raiz(pos[r.id_b])
        if ra != rb:
            pai[max(ra, rb)] = min(ra, rb)
    chave = pd.DataFrame({c: _numerico(d[c]) if c in d else 0 for c in _ORDEM})
    chave["id"] = d["id"]
    ordem = chave.sort_values(_ORDEM + ["id"], kind="mergesort").index
    raizes = [raiz(k) for k in range(len(d))]
    primeiro = {}
    for k in ordem:   # o primeiro de cada componente na ordem de publicação é o representante
        primeiro.setdefault(raizes[k], k)
    d["grupo"] = [d["id"].iloc[primeiro[r]] for r in raizes]
    d["representante"] = [primeiro[r] == k for k, r in enumerate(raizes)]
    return d


def _tabela(d, coluna):
    # grupos = representantes na categoria (um grupo que atravessa categorias conta onde está o representante)
    t = d.groupby(coluna, dropna=False).agg(anuncios=("id", "size"), grupos=("representante", "sum")).reset_index()
    t["perde_pct"] = 100 * (t["anuncios"] - t["grupos"]) / t["anuncios"]
    return t


def resumo(df_agrupado):
    """{'anuncios', 'grupos', 'removiveis', 'perde_pct', 'por_tipo', 'por_periodo', 'por_bib'}; as tabelas têm
    anuncios, grupos e perde_pct (% de anúncios que se perde ficando só com o representante)."""
    d = df_agrupado
    n, g = len(d), d["grupo"].nunique()
    return {"anuncios": n, "grupos": g, "removiveis": int((~d["representante"]).sum()),
            "perde_pct": 100 * (n - g) / n if n else 0.0,
            "por_tipo": _tabela(d, "c_tipo"), "por_periodo": _tabela(d, "periodo_legal"), "por_bib": _tabela(d, "bib")}
