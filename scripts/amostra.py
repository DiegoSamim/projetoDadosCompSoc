"""Amostra do grupo: poucas páginas, bem variadas (4 períodos legais x 5 tipos de anúncio).

Cada linha de AMOSTRA é uma "célula": um termo num acervo, com quantas páginas listar e quantas capturar.
O plano e o porquê de cada escolha estão em termos_busca.md (seção "O que vamos buscar").

    PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao                # o que já foi feito, célula por célula
    PYTHONPATH=src .venv/bin/python scripts/amostra.py listar --pessoa 2       # sem CAPTCHA, roda sozinho
    PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar --pessoa 2     # precisa de uma pessoa para o CAPTCHA

`--pessoa 1|2|3` limita às células daquela pessoa (divisão em planejamento.md); sem ele, vale a amostra inteira.
`--extras` troca a amostra pela lista EXTRAS (dados a mais, para os períodos fracos). O `capturar` sem `--extras`
nunca pega as páginas extras, então quem só captura a amostra não é atrapalhado.
`--complemento` usa a lista COMPLEMENTO: mais dados para quem tem tempo de sobra (variedade de termos, mulheres,
cores, e um segundo jornal). Vem depois da amostra e dos extras.

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
LISTAR_EXTRAS = 60      # nas células extras, menos: só precisamos de poucas páginas

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

# Dados a mais, fora da amostra principal: reforçam 1871–1888 (só 25 anúncios) e "antes de 1831" (só fuga).
# O Diário do RJ (094170_01) tem OCR rápido (cerca de 6 s por página) e, na ordem de data, as primeiras páginas
# são de 1821 em diante, ou seja, "antes de 1831". Termos "Contexto" servem para ligar os anúncios às leis.
EXTRAS = [
    ("1871–1888",     "fuga",         "364568_06", "JC 1870s",   '"escravo fugido"',       5),
    ("1871–1888",     "fuga",         "364568_06", "JC 1870s",   '"escrava fugida"',       3),
    ("1871–1888",     "fuga",         "364568_07", "JC 1880s",   '"escravo fugido"',       5),
    ("1871–1888",     "fuga",         "364568_07", "JC 1880s",   '"escrava fugida"',       3),
    ("1871–1888",     "contexto",     "364568_06", "JC 1870s",   'ingenuo',                3),
    ("1871–1888",     "contexto",     "364568_07", "JC 1880s",   'sexagenario',            3),
    ("antes de 1831", "venda",        "094170_01", "DRJ 1821–58", '"vende-se uma preta"',  4),
    ("antes de 1831", "venda",        "094170_01", "DRJ 1821–58", '"vende-se um preto"',   4),
    ("antes de 1831", "aluguel",      "094170_01", "DRJ 1821–58", '"aluga-se uma preta"',  4),
    ("antes de 1831", "aluguel",      "094170_01", "DRJ 1821–58", '"aluga-se um preto"',   3),
    ("antes de 1831", "ama de leite", "094170_01", "DRJ 1821–58", '"preta com leite"',     4),
    ("antes de 1831", "fuga",         "094170_01", "DRJ 1821–58", '"fugio um escravo"',    4),
    ("antes de 1831", "compra",       "094170_01", "DRJ 1821–58", '"compra-se um preto"',  2),
]

# Complemento: para quem terminou a amostra e os extras e tem tempo. Quatro objetivos:
#   a) mais densidade nos anos 1850–1860, onde cada página rende pouco;
#   b) mais mulheres (hoje a fuga é quase toda masculina) e ama de leite em mais décadas;
#   c) variedade de cor e de redação ("parda", "crioula"), além de "preta";
#   d) um segundo jornal para o mesmo período (última parte da lista), que mostra se o padrão é só do Jornal do Commercio.
COMPLEMENTO = [
    ("1850–1871",     "fuga",         "364568_04", "JC 1850s",   '"escravo fugido"',       6),
    ("1850–1871",     "fuga",         "364568_04", "JC 1850s",   '"preto fugido"',         4),
    ("1850–1871",     "fuga",         "364568_05", "JC 1860s",   '"escravo fugido"',       6),
    ("1850–1871",     "fuga",         "364568_05", "JC 1860s",   '"escrava fugida"',       4),
    ("1850–1871",     "fuga",         "364568_05", "JC 1860s",   '"preto fugido"',         4),
    ("1850–1871",     "fuga",         "364568_04", "JC 1850s",   '"preta fugida"',         4),
    ("1871–1888",     "fuga",         "364568_06", "JC 1870s",   '"preta fugida"',         4),
    ("1831–1850",     "fuga",         "364568_03", "JC 1840s",   '"fugio o preto"',        4),
    ("1831–1850",     "fuga",         "364568_03", "JC 1840s",   '"fugio o escravo"',      4),
    ("1850–1871",     "ama de leite", "364568_04", "JC 1850s",   '"escrava com leite"',    4),
    ("1850–1871",     "ama de leite", "364568_05", "JC 1860s",   '"crioula com leite"',    4),
    ("1871–1888",     "ama de leite", "364568_06", "JC 1870s",   '"escrava com leite"',    4),
    ("1831–1850",     "aluguel",      "364568_03", "JC 1840s",   '"aluga-se uma parda"',   4),
    ("1850–1871",     "aluguel",      "364568_04", "JC 1850s",   '"aluga-se uma parda"',   4),
    ("1850–1871",     "aluguel",      "364568_05", "JC 1860s",   '"aluga-se uma crioula"', 4),
    ("1850–1871",     "venda",        "364568_04", "JC 1850s",   '"vende-se uma parda"',   4),
    ("1850–1871",     "venda",        "364568_05", "JC 1860s",   '"vende-se uma crioula"', 3),
    ("1850–1871",     "compra",       "364568_04", "JC 1850s",   '"compra-se uma preta"',  4),
    ("1850–1871",     "compra",       "364568_04", "JC 1850s",   '"compra-se uma escrava"', 4),
    # segundo jornal, do mesmo período (só vale se o site responder para estes acervos)
    ("1850–1871",     "fuga",         "094170_02", "DRJ 1860–78", '"escravo fugido"',      6),
    ("1850–1871",     "fuga",         "217280",    "Correio Mercantil", '"escrav* fugid*"', 6),
]

# quem fica com cada período (planejamento.md, "Quem faz o quê")
PESSOAS = {1: ["1871–1888"], 2: ["antes de 1831", "1831–1850"], 3: ["1850–1871"]}


def celulas(pessoa=None, extras=False, complemento=False):
    """As células da amostra (ou das EXTRAS ou do COMPLEMENTO), ou só as da pessoa."""
    lista = COMPLEMENTO if complemento else EXTRAS if extras else AMOSTRA
    return [c for c in lista if pessoa is None or c[0] in PESSOAS[pessoa]]


def andamento(banco):
    """(bib, termo) -> {listadas, total, ok, erro}, a partir do relatório do banco."""
    feito = {}
    for b in banco.relatorio()["buscas"]:
        feito[(b["bib"], b["termo"])] = {"listadas": b["listadas"], "total": b["total_servidor"],
                                         "ok": b["paginas"].get("ok", 0), "erro": b["paginas"].get("erro", 0)}
    return feito


def situacao(banco, pessoa=None, extras=False, complemento=False):
    feito = andamento(banco)
    print(f"{'período':14} {'tipo':13} {'acervo':11} {'termo':24} {'listadas':>9} {'capturadas':>11}")
    total_ok = total_meta = 0
    for periodo, tipo, bib, acervo, termo, meta in celulas(pessoa, extras, complemento):
        f = feito.get((bib, termo), {})
        ok = min(f.get("ok", 0), meta)
        total_ok, total_meta = total_ok + ok, total_meta + meta
        listadas = f"{f['listadas']}/{f['total']}" if f else "—"
        print(f"{periodo:14} {tipo:13} {acervo:11} {termo:24} {listadas:>9} {f.get('ok', 0):>5} de {meta}")
    print(f"\nCapturadas: {total_ok} de {total_meta} páginas {'do complemento' if complemento else 'extras' if extras else 'da amostra'}.")


def listar(banco, pessoa=None, extras=False, complemento=False):
    sessao = nova_sessao()
    limite = LISTAR_EXTRAS if extras or complemento else LISTAR_NO_MAXIMO
    for periodo, tipo, bib, acervo, termo, _ in celulas(pessoa, extras, complemento):
        salvas, total = coletar_ocorrencias(sessao, bib, termo, banco, limite=limite)
        print(f"{periodo:14} {tipo:13} {acervo:11} {termo:24} {salvas} listadas de {total}", flush=True)


def capturar(banco, quem, modo, pessoa=None, extras=False, complemento=False):
    from hdb.captura import capturar as capturar_paginas

    feito = andamento(banco)
    for periodo, tipo, bib, acervo, termo, meta in celulas(pessoa, extras, complemento):
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
    p.add_argument("--extras", action="store_true", help="usa a lista EXTRAS (dados a mais) em vez da amostra")
    p.add_argument("--complemento", action="store_true", help="usa a lista COMPLEMENTO (mais dados, para quem tem tempo)")
    p.add_argument("--pessoa", type=int, choices=sorted(PESSOAS), help="só as células desta pessoa")
    args = p.parse_args()
    banco = BancoSupabase()
    if args.etapa == "listar":
        listar(banco, args.pessoa, args.extras, args.complemento)
    elif args.etapa == "capturar":
        capturar(banco, args.quem, args.modo, args.pessoa, args.extras, args.complemento)
    situacao(banco, args.pessoa, args.extras, args.complemento)


if __name__ == "__main__":
    main()
