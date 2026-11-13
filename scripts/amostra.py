"""Amostra do grupo: poucas páginas, bem variadas (4 períodos legais x 5 tipos de anúncio).

Cada linha de AMOSTRA é uma "célula": um termo num acervo, com quantas páginas listar e quantas capturar.
O plano e o porquê de cada escolha estão em termos_busca.md (seção "O que vamos buscar").

    PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao                # o que já foi feito, célula por célula
    PYTHONPATH=src .venv/bin/python scripts/amostra.py listar --pessoa 2       # sem CAPTCHA, roda sozinho
    PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar --pessoa 2     # precisa de uma pessoa para o CAPTCHA

`--pessoa 1|2|3` limita às células daquela pessoa (divisão em planejamento.md); sem ele, vale a amostra inteira.

Tudo é retomável: rodar de novo continua de onde parou e não repete páginas.
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hdb import config  # noqa: E402
from hdb.banco import BancoSupabase  # noqa: E402
from hdb.busca import coletar_ocorrencias, nova_sessao  # noqa: E402

LISTAR_NO_MAXIMO = 200  # ocorrências listadas por célula (a lista sai em ordem de data)

# (período legal, tipo, bib, acervo, termo, páginas a capturar)
AMOSTRA = [
    ("antes de 1831", "fuga",         "364568_01", "JC 1827–29", '"escravos fugidos"',     4),
    ("antes de 1831", "venda",        "364568_01", "JC 1827–29", '"vende-se uma preta"',   4),
    ("antes de 1831", "aluguel",      "364568_01", "JC 1827–29", '"aluga-se uma preta"',   3),
    ("antes de 1831", "ama de leite", "364568_01", "JC 1827–29", '"preta com leite"',      3),
    ("antes de 1831", "compra",       "364568_01", "JC 1827–29", '"compra-se escravos"',   1),
    ("1831–1850",     "fuga",         "364568_02", "JC 1830s",   '"escravos fugidos"',     4),
    ("1831–1850",     "venda",        "364568_02", "JC 1830s",   '"vende-se uma preta"',   4),
    ("1831–1850",     "aluguel",      "364568_02", "JC 1830s",   '"aluga-se uma preta"',   4),
    ("1831–1850",     "ama de leite", "364568_02", "JC 1830s",   '"preta com leite"',      4),
    ("1831–1850",     "compra",       "364568_02", "JC 1830s",   '"compra-se um moleque"', 2),
    ("1850–1871",     "fuga",         "364568_05", "JC 1860s",   '"fugio o escravo"',      4),
    ("1850–1871",     "venda",        "364568_05", "JC 1860s",   '"vende-se uma preta"',   4),
    ("1850–1871",     "aluguel",      "364568_05", "JC 1860s",   '"aluga-se uma escrava"', 4),
    ("1850–1871",     "ama de leite", "364568_05", "JC 1860s",   '"preta com leite"',      4),
    ("1850–1871",     "compra",       "364568_05", "JC 1860s",   '"compra-se escravos"',   2),
    ("1871–1888",     "fuga",         "364568_06", "JC 1870s",   '"fugio o escravo"',      4),
    ("1871–1888",     "venda",        "364568_06", "JC 1870s",   '"vende-se uma preta"',   4),
    ("1871–1888",     "aluguel",      "364568_06", "JC 1870s",   '"aluga-se uma escrava"', 4),
    ("1871–1888",     "ama de leite", "364568_06", "JC 1870s",   '"preta com leite"',      4),
    ("1871–1888",     "compra",       "364568_06", "JC 1870s",   '"compra-se escravos"',   2),
]

# quem fica com cada período (planejamento.md, "Quem faz o quê")
PESSOAS = {1: ["1871–1888"], 2: ["antes de 1831", "1831–1850"], 3: ["1850–1871"]}


def celulas(pessoa=None):
    """As células da amostra, ou só as da pessoa."""
    return [c for c in AMOSTRA if pessoa is None or c[0] in PESSOAS[pessoa]]


def andamento(banco):
    """(bib, termo) -> {listadas, total, ok, erro}, a partir do relatório do banco."""
    feito = {}
    for b in banco.relatorio()["buscas"]:
        feito[(b["bib"], b["termo"])] = {"listadas": b["listadas"], "total": b["total_servidor"],
                                         "ok": b["paginas"].get("ok", 0), "erro": b["paginas"].get("erro", 0)}
    return feito


def situacao(banco, pessoa=None):
    feito = andamento(banco)
    print(f"{'período':14} {'tipo':13} {'acervo':11} {'termo':24} {'listadas':>9} {'capturadas':>11}")
    total_ok = total_meta = 0
    for periodo, tipo, bib, acervo, termo, meta in celulas(pessoa):
        f = feito.get((bib, termo), {})
        ok = min(f.get("ok", 0), meta)
        total_ok, total_meta = total_ok + ok, total_meta + meta
        listadas = f"{f['listadas']}/{f['total']}" if f else "—"
        print(f"{periodo:14} {tipo:13} {acervo:11} {termo:24} {listadas:>9} {f.get('ok', 0):>5} de {meta}")
    print(f"\nCapturadas: {total_ok} de {total_meta} páginas da amostra.")


def listar(banco, pessoa=None):
    sessao = nova_sessao()
    for periodo, tipo, bib, acervo, termo, _ in celulas(pessoa):
        salvas, total = coletar_ocorrencias(sessao, bib, termo, banco, limite=LISTAR_NO_MAXIMO)
        print(f"{periodo:14} {tipo:13} {acervo:11} {termo:24} {salvas} listadas de {total}", flush=True)


def capturar(banco, quem, modo, pessoa=None):
    from hdb.captura import capturar as capturar_paginas

    feito = andamento(banco)
    for periodo, tipo, bib, acervo, termo, meta in celulas(pessoa):
        falta = meta - feito.get((bib, termo), {}).get("ok", 0)
        if falta <= 0:
            continue
        print(f"\n== {periodo} · {tipo} · {acervo} · {termo}: faltam {falta} páginas", flush=True)
        # as imagens ficam em data/amostra porque `hdb anuncios` ainda precisa delas (planejamento, 3.1)
        capturar_paginas(banco, quem, bib=bib, termo=termo, max_paginas=falta, aleatorio=True, modo=modo,
                         guardar=config.AMOSTRA_DIR)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("etapa", choices=["situacao", "listar", "capturar"], nargs="?", default="situacao")
    p.add_argument("--quem", default=getpass.getuser(), help="quem captura (padrão: usuário do sistema)")
    p.add_argument("--modo", choices=["terminal", "janela"], default="terminal",
                   help="onde a pessoa resolve o CAPTCHA (padrão: terminal)")
    p.add_argument("--pessoa", type=int, choices=sorted(PESSOAS), help="só as células desta pessoa")
    args = p.parse_args()
    banco = BancoSupabase()
    if args.etapa == "listar":
        listar(banco, args.pessoa)
    elif args.etapa == "capturar":
        capturar(banco, args.quem, args.modo, args.pessoa)
    situacao(banco, args.pessoa)


if __name__ == "__main__":
    main()
