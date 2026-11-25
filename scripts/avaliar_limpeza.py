"""Avalia a limpeza (classificação de tipo + seleção do corpus) contra a conferência manual.

Lê tests/fixtures/conferencia.json: lista de {"id", "periodo", "texto", "tipo_c4", "e_anuncio", "tipo_certo"}.
Roda o código atual (`campos.classificar` e `corpus.motivo_descarte`) em cada item e compara com o corpus antigo
(todos os itens entravam nele, com o tipo `tipo_c4`). Itens com `e_anuncio` nulo (texto cortado) ficam de fora da conta. Sai com código 1 se as metas falharem:
ruído no corpus cair menos de 50% em relação ao antigo, ou perdidos > 3% dos anúncios verdadeiros.

Uso: PYTHONPATH=src python scripts/avaliar_limpeza.py [conferencia.json]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from hdb import campos, corpus  # noqa: E402

ARQUIVO = RAIZ / "tests" / "fixtures" / "conferencia.json"
CONFIANCA = 90  # a conferência não guarda a confiança do OCR; só importam tipo, tamanho do texto e o corte
META_QUEDA_RUIDO = 0.5
META_PERDIDOS = 0.03
TIPOS_DE_PESSOA = ("fuga", "venda", "compra", "aluguel")


def carregar(arquivo=ARQUIVO):
    arquivo = Path(arquivo)
    if not arquivo.exists():
        raise SystemExit(f"erro: conferência não encontrada em {arquivo}\n"
                         "(é o arquivo com os anúncios conferidos à mão: lista de "
                         '{"id", "periodo", "texto", "tipo_c4", "e_anuncio", "tipo_certo"})')
    return json.loads(arquivo.read_text(encoding="utf-8"))


def entra(tipo, texto):
    return corpus.motivo_descarte({"c_tipo": tipo, "texto": texto, "confianca": CONFIANCA}) is None


def classificar(item):
    """Tipo pelo código atual, com título e abertura que o banco guardou (a segmentação os dá; o texto sozinho não)."""
    return campos.classificar({"texto": item["texto"], "titulo": item.get("titulo"), "abertura": item.get("abertura")})[0]


def _pessoa(tipo):
    return tipo in TIPOS_DE_PESSOA


def avaliar(itens):
    """Números por período e no total; cada período tem as mesmas chaves."""
    zero = lambda: dict(n=0, verdadeiros=0, entram=0, entram_c4=0, ruido=0, ruido_c4=0,
                        perdidos=0, perdidos_c4=0, tipo_certo=0, tipo_certo_c4=0)
    por_periodo = defaultdict(zero)
    for it in itens:
        tipo = classificar(it)
        if it["e_anuncio"] is None:  # incerto (texto cortado pelo OCR): não entra na conta
            continue
        verdadeiro = bool(it["e_anuncio"])
        # a conferência foi sorteada do corpus antigo (corp2): todo item entrava lá, com o tipo `tipo_c4`
        entra_novo, entra_velho = entra(tipo, it["texto"]), True
        for d in (por_periodo[it.get("periodo") or "?"], por_periodo["TOTAL"]):
            d["n"] += 1
            d["entram"] += entra_novo
            d["entram_c4"] += entra_velho
            if verdadeiro:
                d["verdadeiros"] += 1
                d["tipo_certo"] += tipo == it["tipo_certo"]
                d["tipo_certo_c4"] += it["tipo_c4"] == it["tipo_certo"]
                pessoa = _pessoa(it["tipo_certo"])
                d["perdidos"] += pessoa and not entra_novo
                d["perdidos_c4"] += pessoa and not entra_velho
            else:
                d["ruido"] += entra_novo
                d["ruido_c4"] += entra_velho
    return dict(por_periodo)


def _pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "-"


def metas(total):
    """(ok, mensagens) das duas metas sobre o total."""
    ruido, ruido_c4 = total["ruido"], total["ruido_c4"]
    queda = (ruido_c4 - ruido) / ruido_c4 if ruido_c4 else 1.0
    perda = total["perdidos"] / total["verdadeiros"] if total["verdadeiros"] else 0.0
    ok_ruido, ok_perda = queda >= META_QUEDA_RUIDO, perda <= META_PERDIDOS
    return ok_ruido and ok_perda, [
        f"meta ruído: queda de {100 * queda:.0f}% (meta: pelo menos {100 * META_QUEDA_RUIDO:.0f}%) - "
        + ("ok" if ok_ruido else "FALHOU"),
        f"meta perdidos: {100 * perda:.1f}% dos verdadeiros (meta: no máximo {100 * META_PERDIDOS:.0f}%) - "
        + ("ok" if ok_perda else "FALHOU")]


def imprimir(resultado):
    t = resultado["TOTAL"]
    print(f"Conferência: {t['n']} itens, {t['verdadeiros']} anúncios de verdade.\n")
    print(f"Entram no corpus:  {t['entram']} (código antigo c4: {t['entram_c4']})")
    print(f"Ruído no corpus:   {t['ruido']} (c4: {t['ruido_c4']}) - entram sem ser anúncio")
    print(f"Perdidos:          {t['perdidos']} (c4: {t['perdidos_c4']}) - anúncios de pessoa que ficam de fora")
    print(f"Tipo certo:        {t['tipo_certo']} de {t['verdadeiros']} ({_pct(t['tipo_certo'], t['verdadeiros'])}; "
          f"c4: {_pct(t['tipo_certo_c4'], t['verdadeiros'])})\n")
    cab = f"{'período':<36}{'n':>5}{'entram':>8}{'ruído':>7}{'(c4)':>6}{'perdidos':>10}{'(c4)':>6}{'tipo certo':>12}"
    print(cab + "\n" + "-" * len(cab))
    for periodo in sorted(p for p in resultado if p != "TOTAL") + ["TOTAL"]:
        d = resultado[periodo]
        print(f"{periodo:<36}{d['n']:>5}{d['entram']:>8}{d['ruido']:>7}{d['ruido_c4']:>6}{d['perdidos']:>10}"
              f"{d['perdidos_c4']:>6}{_pct(d['tipo_certo'], d['verdadeiros']):>12}")
    print()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    resultado = avaliar(carregar(argv[0] if argv else ARQUIVO))
    imprimir(resultado)
    ok, mensagens = metas(resultado["TOTAL"])
    print("\n".join(mensagens))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
