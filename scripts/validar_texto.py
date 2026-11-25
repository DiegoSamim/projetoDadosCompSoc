"""Valida a segmentação pelo texto (v2t) contra a segmentação com posições (v2), só lendo o banco.

Para cada página que tem anúncios v2 e texto do OCR, roda `separar_texto` em memória (não grava) e compara:
nº de anúncios v2 e v2t, e a fração dos anúncios v2 cujo início (6 primeiras palavras, sem acento) aparece como
início de algum anúncio v2t da mesma página. Imprime a tabela por acervo e o total.

A segmentação por texto só vale para páginas de poucas colunas e anúncios numerados (o Diário do Rio, o JC dos
anos 1820 e 1830). Nos jornais de várias colunas o Tesseract emenda linhas vizinhas e a taxa cai a 5%–35%: isso é
esperado e **não** reprova o método. O código de saída é 1 se a taxa exata dos acervos de layout parecido
(`ACERVOS_NUMERADOS`) ficar abaixo de `META` (70%).

Títulos de seção que o v2 separou como anúncio ("ESCRAVOS FUGIDOS") não entram na conta: no v2t viram `titulo`.
Mostra também a taxa aproximada (início parecido, similaridade >= 0.75), porque o v2 vem de outra leitura do OCR
(palavras) e o texto do v2t (leitura do texto) difere em letras soltas; a meta vale para a taxa exata.

Uso: PYTHONPATH=src python scripts/validar_texto.py
"""
import sys
import unicodedata
from difflib import SequenceMatcher
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hdb.anuncios import e_secao  # noqa: E402
from hdb.anuncios_texto import SECOES_EXTRAS, separar_texto  # noqa: E402
from hdb import config  # noqa: E402

META = 0.70
ACERVOS_NUMERADOS = ("094170_01",)  # o Diário do Rio (anos 1820): o layout mais parecido com o JC de 1827–1839
SIMILARIDADE = 0.75
PALAVRAS = 6


def inicio(texto, n=PALAVRAS):
    """As `n` primeiras palavras do texto, minúsculas, sem acento nem pontuação."""
    sem = unicodedata.normalize("NFD", (texto or "").lower())
    sem = "".join(c if c.isalnum() or c.isspace() else " " for c in sem if unicodedata.category(c) != "Mn")
    return " ".join(sem.split()[:n])


def e_titulo_de_secao(texto):
    return bool(texto) and len(texto) <= 40 and e_secao(texto, config.ANUNCIO_SECOES + SECOES_EXTRAS, 2)


def comparar_pagina(anuncios_v2, texto, confianca=None):
    """(n_v2, n_v2t, v2 reencontrados exatos, v2 reencontrados aproximados) de uma página.

    Os v2 que são só título de seção não contam (nem em n_v2).
    """
    novos = separar_texto(texto, confianca)
    inicios = {inicio(a["texto"]) for a in novos}
    contados = [inicio(a.get("texto")) for a in anuncios_v2 if not e_titulo_de_secao(a.get("texto"))]
    exatos = sum(1 for i in contados if i in inicios)
    aprox = sum(1 for i in contados if i in inicios or any(SequenceMatcher(None, i, j).ratio() >= SIMILARIDADE
                                                          for j in inicios))
    return len(contados), len(novos), exatos, aprox


def main():
    from hdb.cli import _banco

    banco = _banco()
    paginas = {p["id"]: p for p in _todas_paginas(banco)}
    por_acervo = defaultdict(lambda: [0, 0, 0, 0, 0])  # páginas, n_v2, n_v2t, exatos, aproximados
    for pagina_id in sorted(banco.paginas_com_anuncios("v2")):
        texto, conf = banco.texto_da_pagina(pagina_id)
        if not texto:
            continue
        v2 = banco.anuncios(pagina_id, "v2")
        n2, nt, achados, aprox = comparar_pagina(v2, texto, conf)
        linha = por_acervo[paginas.get(pagina_id, {}).get("bib", "?")]
        linha[0] += 1
        linha[1] += n2
        linha[2] += nt
        linha[3] += achados
        linha[4] += aprox
    print(f"{'acervo':<12}{'páginas':>8}{'v2':>8}{'v2t':>8}{'iguais':>8}{'taxa':>8}{'aprox.':>8}")
    total = [0] * 5
    for bib, l in sorted(por_acervo.items()):
        print(f"{bib:<12}{l[0]:>8}{l[1]:>8}{l[2]:>8}{l[3]:>8}{(l[3] / l[1] if l[1] else 0):>8.1%}"
              f"{(l[4] / l[1] if l[1] else 0):>8.1%}")
        total = [a + b for a, b in zip(total, l)]
    taxa = total[3] / total[1] if total[1] else 0.0
    num = [por_acervo[b] for b in ACERVOS_NUMERADOS if b in por_acervo]
    taxa_num = sum(l[3] for l in num) / max(sum(l[1] for l in num), 1)
    print(f"{'TOTAL':<12}{total[0]:>8}{total[1]:>8}{total[2]:>8}{total[3]:>8}{taxa:>8.1%}"
          f"{(total[4] / total[1] if total[1] else 0):>8.1%}  (informativo: várias colunas)")
    print(f"{'NUMERADOS':<12}{'':>32}{taxa_num:>8.1%}  (meta {META:.0%} na taxa exata, acervos {', '.join(ACERVOS_NUMERADOS)})")
    return 0 if taxa_num >= META else 1


def _todas_paginas(banco):
    from hdb.banco import _todas

    return _todas(banco.cliente.table("paginas").select("id,bib").order("id"))


if __name__ == "__main__":
    sys.exit(main())
