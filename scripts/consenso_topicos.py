"""Consenso do LDA entre sementes: estabilidade de cada tema e intervalo da parcela por período.

Uso: python scripts/consenso_topicos.py [--sementes N] [--rapido]
Lê o corpus como `hdb topicos` (corp3, 6 tópicos), treina o LDA com N sementes e guarda um resumo pequeno em
data/consenso_topicos.json (só estabilidades e parcelas; nada de anúncios individuais). Não grava nada no banco.
"""
import argparse
import json
import time
from pathlib import Path

from hdb import config, consenso
from hdb.cli import _banco

SAIDA = Path(__file__).resolve().parents[1] / "data" / "consenso_topicos.json"
PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sementes", type=int, default=consenso.N_SEMENTES, help="nº de sementes (padrão 30)")
    ap.add_argument("--rapido", action="store_true", help="só 5 sementes (teste)")
    args = ap.parse_args(argv)
    n = 5 if args.rapido else args.sementes

    docs = [d for d in _banco().anuncios_do_corpus(config.VERSAO_CORPUS) if (d.get("texto_padrao") or "").strip()]
    docs = [d for d in docs if isinstance(d.get("periodo_legal"), str)]
    textos = [d["texto_padrao"] for d in docs]
    periodos = [consenso.periodo_curto(d["periodo_legal"]) for d in docs]
    print(f"{len(docs)} anúncios do corpus {config.VERSAO_CORPUS}; 6 tópicos; {n} sementes")
    inicio = time.monotonic()
    r = consenso.calcular(textos, periodos, 6, n, ordem=[p for p in PERIODOS if p in set(periodos)],
                          progresso=lambda i, t: print(f"  semente {i}/{t} ({time.monotonic() - inicio:.0f} s)", flush=True))
    r.update(versao_corpus=config.VERSAO_CORPUS, n_topicos=6, segundos=round(time.monotonic() - inicio))

    print(f"\nSemente de referência: {r['semente_ref']}; limiar JS = {r['limiar']:.3f} "
          f"(mediana das distâncias entre temas da referência / 2); instável se estabilidade < {r['min_estavel']:.0%}")
    cab = " | ".join(f"{p:>26}" for p in r["periodos"])
    print(f"\n{'tema':<52} {'estab.':>6}  {cab}")
    for t in r["temas"]:
        cel = " | ".join(f"{t['parcela'][p]['mediana']:6.1%} [{t['parcela'][p]['p2_5']:5.1%}; {t['parcela'][p]['p97_5']:5.1%}]"
                         for p in r["periodos"])
        print(f"{t['nome'][:50]:<52} {t['estabilidade']:>6.0%}  {cel}" + ("  INSTÁVEL" if t["instavel"] else ""))

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ngravado {SAIDA}")


if __name__ == "__main__":
    main()
