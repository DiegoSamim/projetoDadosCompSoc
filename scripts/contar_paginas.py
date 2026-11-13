"""Descobre quantas páginas tem cada acervo da HDB (só leitura, sem CAPTCHA).

O leitor volta para a página 1 quando se pede uma página que não existe, então o total sai de uma
busca binária pela maior página válida. Serve de denominador para as contagens de
scripts/contar_termos.py: "o termo aparece em X% das páginas".
Resultado: data/paginas_por_acervo.csv

    PYTHONPATH=src python scripts/contar_paginas.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contar_termos import ACERVOS  # noqa: E402
from hdb import config  # noqa: E402
from hdb.acervos import total_de_paginas  # noqa: E402
from hdb.busca import nova_sessao  # noqa: E402

SAIDA = config.DATA_DIR / "paginas_por_acervo.csv"


def main():
    sessao = nova_sessao()
    linhas = []
    for bib, nome in ACERVOS:
        total = total_de_paginas(sessao, bib)
        linhas.append({"bib": bib, "acervo": nome, "paginas": total})
        print(f"{bib} {nome:12} {total} páginas", flush=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["bib", "acervo", "paginas"])
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
