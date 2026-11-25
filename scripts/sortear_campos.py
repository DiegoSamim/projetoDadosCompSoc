"""Sorteia os anúncios que serão rotulados à mão para validar os campos (recompensa, nação, idade, sexo, marcas).

Sorteia 80 fugas (20 por período legal) e 40 aluguéis (10 por período) do corpus, com semente fixa, fora os ids
das conferências anteriores. Grava tests/fixtures/campos_gold.json: lista de {"id", "periodo", "tipo", "texto"}, com o
texto ORIGINAL (espaços normalizados, até 700 caracteres) e sem rótulos nem o que o código extraiu. Quem rotula
acrescenta a chave `rotulos` (formato em hdb.validacao). Não sobrescreve arquivo com rótulos, a não ser com --forcar.
Só lê o banco.

Uso: PYTHONPATH=src python scripts/sortear_campos.py [--forcar]
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
CONFERENCIAS = (FIXTURES / "conferencia.json", FIXTURES / "conferencia_extra.json")


def periodo_curto(p):
    if not isinstance(p, str):
        return None
    return p if p.startswith("antes") else p.split(" ")[0]


def ids_excluidos(arquivos=CONFERENCIAS):
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


def main(argv=None, banco=None, saida=SAIDA, textos=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--forcar", action="store_true", help="sobrescreve o arquivo mesmo com rótulos")
    args = ap.parse_args(argv)
    if tem_rotulos(saida) and not args.forcar:
        print(f"{saida} já tem rótulos (chave `rotulos`); não sobrescrevo. Use --forcar para sobrescrever.")
        return 1
    if banco is None:
        from hdb.banco import BancoSupabase
        banco = BancoSupabase()
    itens = sortear(banco, textos if textos is not None else ler_textos(banco), ids_excluidos())
    Path(saida).write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(itens)} anúncios gravados em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
