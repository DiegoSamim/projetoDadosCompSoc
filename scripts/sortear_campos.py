"""Sorteia os anúncios que serão rotulados à mão para validar os campos (recompensa, nação, idade, sexo, marcas).

Sorteia fugas (--fugas por período legal, padrão 20) e aluguéis (--alugueis por período, padrão 10; 0 não sorteia
nenhum) do corpus, com semente fixa (--semente), fora os ids das conferências anteriores e do próprio
tests/fixtures/campos_gold.json (o conjunto de desenvolvimento). Grava em --saida (padrão: o gold): lista de {"id", "periodo", "tipo", "texto"}, com o
texto ORIGINAL (espaços normalizados, até 700 caracteres) e sem rótulos nem o que o código extraiu. Quem rotula
acrescenta a chave `rotulos` (formato em hdb.validacao). Não sobrescreve arquivo com rótulos, a não ser com --forcar.
Só lê o banco.

Uso: PYTHONPATH=src python scripts/sortear_campos.py [--saida ARQ] [--fugas N] [--alugueis N] [--semente S] [--forcar]
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from hdb import config  # noqa: E402

SEMENTE = 20251125
PEDIDOS = {"fuga": 20, "aluguel": 10}  # por período
PERIODOS = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
MAX_CARACTERES = 700
FIXTURES = RAIZ / "tests" / "fixtures"
SAIDA = FIXTURES / "campos_gold.json"
CONFERENCIAS = (FIXTURES / "conferencia.json", FIXTURES / "conferencia_extra.json", FIXTURES / "campos_teste.json")  # o teste já usado também não volta


def periodo_curto(p):
    if not isinstance(p, str):
        return None
    return p if p.startswith("antes") else p.split(" ")[0]


def ids_excluidos(arquivos=CONFERENCIAS + (SAIDA,)):
    ids = set()
    for a in arquivos:
        if Path(a).exists():
            ids |= {i["id"] for i in json.loads(Path(a).read_text(encoding="utf-8"))}
    return ids


def ler_textos(banco):
    """{id: texto original} da view anuncios_completos (versões de anúncios e campos atuais)."""
    from hdb.banco import _todas
    linhas = _todas(banco.cliente.table("anuncios_completos").select("id,texto")
                    .in_("versao", list(config.VERSOES_ANUNCIOS)).eq("c_versao", config.VERSAO_CAMPOS).order("id"))
    return {l["id"]: l["texto"] for l in linhas}


def sortear(banco, textos, excluir=(), semente=SEMENTE, pedidos=PEDIDOS, aviso=print):
    """Lista de itens sorteados (ordenada por período, tipo e id). `textos` = {id: texto original}."""
    excluir = set(excluir)
    grupos = {}
    for a in banco.anuncios_do_corpus(config.VERSAO_CORPUS):
        per, tipo = periodo_curto(a.get("periodo_legal")), a.get("c_tipo")
        texto = " ".join((textos.get(a["id"]) or "").split())
        if per in PERIODOS and tipo in pedidos and a["id"] not in excluir and texto:
            grupos.setdefault((tipo, per), []).append({"id": a["id"], "periodo": per, "tipo": tipo, "texto": texto[:MAX_CARACTERES]})
    saida = []
    for tipo, n in pedidos.items():
        for per in PERIODOS:
            g = sorted(grupos.get((tipo, per), []), key=lambda i: hashlib.md5(f"{i['id']}{semente}".encode()).hexdigest())
            random.Random(semente).shuffle(g)
            if len(g) < n:
                aviso(f"aviso: {tipo} em {per} tem só {len(g)} anúncios (pedidos {n}); pegando todos")
            saida += g[:n]
    ordem = {p: i for i, p in enumerate(PERIODOS)}
    return sorted(saida, key=lambda i: (list(pedidos).index(i["tipo"]), ordem[i["periodo"]], i["id"]))


def tem_rotulos(arquivo):
    if not Path(arquivo).exists():
        return False
    try:
        return any("rotulos" in i for i in json.loads(Path(arquivo).read_text(encoding="utf-8")))
    except (ValueError, TypeError):
        return False


def main(argv=None, banco=None, saida=None, textos=None, excluir=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--saida", default=None, help=f"arquivo de saída (padrão: {SAIDA})")
    ap.add_argument("--fugas", type=int, default=PEDIDOS["fuga"], help="fugas por período (padrão 20)")
    ap.add_argument("--alugueis", type=int, default=PEDIDOS["aluguel"], help="aluguéis por período (padrão 10; 0 = nenhum)")
    ap.add_argument("--semente", type=int, default=SEMENTE)
    ap.add_argument("--forcar", action="store_true", help="sobrescreve o arquivo mesmo com rótulos")
    args = ap.parse_args(argv)
    saida = Path(args.saida or saida or SAIDA)
    pedidos = {t: n for t, n in (("fuga", args.fugas), ("aluguel", args.alugueis)) if n > 0}
    if tem_rotulos(saida) and not args.forcar:
        print(f"{saida} já tem rótulos (chave `rotulos`); não sobrescrevo. Use --forcar para sobrescrever.")
        return 1
    if banco is None:
        from hdb.banco import BancoSupabase
        banco = BancoSupabase()
    itens = sortear(banco, textos if textos is not None else ler_textos(banco),
                    ids_excluidos() if excluir is None else excluir, semente=args.semente, pedidos=pedidos)
    Path(saida).write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(itens)} anúncios gravados em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
