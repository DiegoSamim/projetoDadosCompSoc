"""Anúncios repetidos no corpus das análises (corp3): grupos por similaridade de texto dentro da janela de edições.

Uso: python scripts/repetidos.py [--limiar 0.6] [--pares ARQ.csv]
Lê o corpus como `medidas.carregar` (sem os temas), agrupa e imprime o resumo. Guarda só {id, grupo, representante}
em data/repetidos.json; --pares grava os pares candidatos (id_a, id_b, similaridade, dist_edicao), sem texto.
Não grava nada no banco.
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd

from hdb import config, repetidos
from hdb.cli import _banco
from hdb.medidas import PERIODOS, _ler_tudo, periodo_curto

SAIDA = Path(__file__).resolve().parents[1] / "data" / "repetidos.json"


def carregar(banco):
    """Mesmo corpus de `medidas.carregar`, com as colunas de posição (edicao, pagina_fisica, ordem)."""
    db = banco.cliente
    corpus = pd.DataFrame(banco.anuncios_do_corpus(config.VERSAO_CORPUS))
    corpus = corpus[corpus["texto_padrao"].fillna("").str.strip() != ""][["id", "periodo_legal", "ano"]]
    extra = _ler_tudo(lambda: db.table("anuncios_completos")
                      .select("id,texto,bib,edicao,pagina_fisica,ordem,c_tipo")
                      .in_("versao", list(config.VERSOES_ANUNCIOS)).eq("c_versao", config.VERSAO_CAMPOS)
                      .order("id")).drop_duplicates("id")
    df = corpus.merge(extra, on="id", how="left")
    ok = df["periodo_legal"].map(lambda p: isinstance(p, str) and periodo_curto(p) in PERIODOS)
    return df[ok].reset_index(drop=True)


def _imprimir(titulo, t, coluna):
    print(f"\n{titulo}")
    for r in t.itertuples():
        print(f"  {str(getattr(r, coluna)):<42} {r.anuncios:>7} anúncios {r.grupos:>7} grupos  {r.perde_pct:5.1f}% se perde")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limiar", type=float, default=repetidos.LIMIAR, help="similaridade mínima para agrupar (padrão 0.6)")
    ap.add_argument("--pares", metavar="ARQ", help="grava os pares candidatos (similaridade ≥ 0.3), sem texto")
    args = ap.parse_args(argv)

    df = carregar(_banco())
    print(f"{len(df)} anúncios do corpus {config.VERSAO_CORPUS}; janela {repetidos.JANELA_EDICOES} edições; limiar {args.limiar}")
    inicio = time.monotonic()
    pares = repetidos.pares_candidatos(df, repetidos.SIMILARIDADE_MIN)
    t_pares = time.monotonic() - inicio
    ag = repetidos.agrupar(df, args.limiar)
    print(f"{len(pares)} pares candidatos (≥ {repetidos.SIMILARIDADE_MIN}); {time.monotonic() - inicio:.1f} s "
          f"({t_pares:.1f} s só nos pares)")
    if args.pares:
        Path(args.pares).parent.mkdir(parents=True, exist_ok=True)
        pares[["id_a", "id_b", "similaridade", "dist_edicao"]].to_csv(args.pares, index=False)
        print(f"pares gravados em {args.pares}")

    r = repetidos.resumo(ag)
    print(f"\n{r['anuncios']} anúncios, {r['grupos']} grupos, {r['removiveis']} removíveis ({r['perde_pct']:.1f}%)")
    _imprimir("Por tipo", r["por_tipo"], "c_tipo")
    _imprimir("Por período", r["por_periodo"], "periodo_legal")
    _imprimir("Por jornal", r["por_bib"], "bib")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps([{"id": int(i) if str(i).isdigit() else i, "grupo": int(g) if str(g).isdigit() else g,
                                  "representante": bool(rep)}
                                 for i, g, rep in zip(ag["id"], ag["grupo"], ag["representante"])], ensure_ascii=False))
    print(f"\ngravado {SAIDA}")


if __name__ == "__main__":
    main()
