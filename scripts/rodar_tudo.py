"""Refaz tudo depois de novos dados: campos, corpus, tópicos, relatório e notebooks.

Uso: python scripts/rodar_tudo.py [--rapido] [--sem-notebooks] [--so PASSO]

Passos, em ordem: campos, corpus, corpus_i, topicos, topicos_i, estabilidade, relatorio, resumo, notebooks.
O passo `resumo` escreve resumo_dados.md (scripts/resumo_dados.py). O passo `notebooks` gera e executa, nesta ordem:
analise_descritiva (gerar_analise), topicos_por_periodo (gerar_topicos), equilibrio_periodos (gerar_equilibrio),
mudanca_por_tipo (gerar_tipos), categorias_por_periodo (gerar_categorias), incerteza (gerar_incerteza) e material_do_grupo (gerar_material).
Cada um roda em um subprocesso (PYTHONPATH=src, mesmo Python). Para no primeiro erro e diz como retomar
(`--so PASSO` roda só aquele). Grava tudo em data/rodar_tudo.log.
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LOG = RAIZ / "data" / "rodar_tudo.log"
NOTEBOOKS = RAIZ / "scripts" / "notebooks"
ULTIMAS = 6
# (gerador, caderno), na ordem em que são gerados e executados
CADERNOS = [("gerar_analise.py", "analise_descritiva"), ("gerar_topicos.py", "topicos_por_periodo"),
            ("gerar_equilibrio.py", "equilibrio_periodos"), ("gerar_tipos.py", "mudanca_por_tipo"),
            ("gerar_categorias.py", "categorias_por_periodo"), ("gerar_incerteza.py", "incerteza"),
            ("gerar_material.py", "material_do_grupo")]


def _hdb(*args):
    return [sys.executable, "-m", "hdb", *args]


def _script(caminho, *args):
    return [sys.executable, str(caminho), *args]


def passos():
    """[(nome, [comandos])] na ordem de execução."""
    return [
        ("campos", [_hdb("campos")]),
        ("corpus", [_hdb("corpus")]),
        ("corpus_i", [_hdb("corpus", "--incluir-incertos", "--versao", "corp3i")]),
        ("topicos", [_hdb("topicos", "--topicos", "6", "--semente", "auto", "--versao", "t5")]),
        ("topicos_i", [_hdb("topicos", "--versao-corpus", "corp3i", "--topicos", "6", "--semente", "auto", "--versao", "t5i")]),
        ("estabilidade", [_script(RAIZ / "scripts" / "estabilidade_topicos.py")]),
        ("relatorio", [_hdb("relatorio")]),
        ("resumo", [_script(RAIZ / "scripts" / "resumo_dados.py")]),
        ("notebooks", [c for gerador, caderno in CADERNOS for c in (
            _script(NOTEBOOKS / gerador), _script(NOTEBOOKS / "executar_notebook.py", str(RAIZ / "notebooks" / f"{caderno}.ipynb")))]),
    ]


NOMES = [n for n, _ in passos()]


def escolher(rapido=False, sem_notebooks=False, so=None):
    todos = passos()
    if so is not None:
        if so not in NOMES:
            raise SystemExit(f"erro: passo desconhecido {so!r}; os passos são: {', '.join(NOMES)}")
        return [p for p in todos if p[0] == so]  # --so ignora --rapido e --sem-notebooks
    pulados = {"estabilidade"} if rapido else set()
    if sem_notebooks:
        pulados.add("notebooks")
    return [p for p in todos if p[0] not in pulados]


def _registrar(texto, log):
    print(texto)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(texto + "\n")


def rodar(selecionados, log=None):
    """Executa os passos; devolve 0 se todos deram certo, 1 no primeiro que falhar."""
    log = log or LOG
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    _registrar(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} - passos: {', '.join(n for n, _ in selecionados)} ===", log)
    inicio_total = time.monotonic()
    for nome, comandos in selecionados:
        inicio = time.monotonic()
        saida, codigo = [], 0
        for comando in comandos:
            r = subprocess.run(comando, cwd=RAIZ, env=env, capture_output=True, text=True)
            saida += [f"$ {' '.join(map(str, comando))}"] + (r.stdout or "").splitlines() + (r.stderr or "").splitlines()
            if r.returncode != 0:
                codigo = r.returncode
                break
        _registrar(f"[{nome}] {'ok' if codigo == 0 else f'FALHOU (código {codigo})'} em {time.monotonic() - inicio:.1f} s", log)
        _registrar("\n".join("    " + l for l in saida[-ULTIMAS:]), log)
        if codigo != 0:
            _registrar(f"\nParou no passo '{nome}'. Corrija o erro acima e retome com:\n"
                       f"    python scripts/rodar_tudo.py --so {nome}\n"
                       "e depois rode os passos seguintes (sem --so, ou um a um com --so).", log)
            return 1
    _registrar(f"\nTudo pronto em {time.monotonic() - inicio_total:.1f} s.", log)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rapido", action="store_true", help="pula a estabilidade dos tópicos (demorada)")
    ap.add_argument("--sem-notebooks", action="store_true", help="não gera nem executa os notebooks")
    ap.add_argument("--so", metavar="PASSO", help=f"roda só este passo ({', '.join(NOMES)})")
    args = ap.parse_args(argv)
    return rodar(escolher(args.rapido, args.sem_notebooks, args.so))


if __name__ == "__main__":
    sys.exit(main())
