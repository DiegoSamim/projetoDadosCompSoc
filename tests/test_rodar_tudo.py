import importlib.util
import subprocess
from pathlib import Path

import pytest

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts" / "rodar_tudo.py"
ORDEM = ["campos", "corpus", "corpus_i", "topicos", "topicos_i", "estabilidade", "relatorio", "resumo", "notebooks"]


@pytest.fixture
def rt(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("rodar_tudo", ARQUIVO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    monkeypatch.setattr(modulo, "LOG", tmp_path / "data" / "rodar_tudo.log")
    return modulo


def simular(monkeypatch, rt, falha_em=None):
    """Troca subprocess.run: guarda os comandos e falha no comando que contém `falha_em`."""
    chamados = []

    def falso(comando, **kw):
        chamados.append(comando)
        erro = falha_em is not None and falha_em in " ".join(map(str, comando))
        return subprocess.CompletedProcess(comando, 2 if erro else 0, stdout="linha1\nlinha2\n", stderr="quebrou" if erro else "")

    monkeypatch.setattr(rt.subprocess, "run", falso)
    return chamados


def nomes(rt, **kw):
    return [n for n, _ in rt.escolher(**kw)]


def test_ordem_e_flags(rt):
    assert nomes(rt) == ORDEM
    assert "estabilidade" not in nomes(rt, rapido=True)
    assert nomes(rt, sem_notebooks=True) == ORDEM[:-1]
    assert nomes(rt, so="topicos_i") == ["topicos_i"]
    assert nomes(rt, so="estabilidade", rapido=True) == ["estabilidade"]
    with pytest.raises(SystemExit):
        rt.escolher(so="xyz")


def test_roda_todos_na_ordem_com_pythonpath_e_log(rt, monkeypatch):
    chamados = simular(monkeypatch, rt)
    assert rt.main(["--sem-notebooks", "--rapido"]) == 0
    assert [c[3] if c[1] == "-m" else Path(c[1]).name for c in chamados] == [
        "campos", "corpus", "corpus", "topicos", "topicos", "relatorio", "resumo_dados.py"]
    assert "--incluir-incertos" in chamados[2] and "corp3i" in chamados[2] and "t5i" in chamados[4]
    log = rt.LOG.read_text(encoding="utf-8")
    assert "[campos] ok" in log and "Tudo pronto" in log


def test_para_no_primeiro_erro_e_diz_como_retomar(rt, monkeypatch, capsys):
    chamados = simular(monkeypatch, rt, falha_em="topicos --topicos 6 --semente auto --versao t5")
    assert rt.main(["--rapido", "--sem-notebooks"]) == 1
    assert len(chamados) == 4  # campos, corpus, corpus_i, topicos (falhou); nada depois
    saida = capsys.readouterr().out
    assert "Parou no passo 'topicos'" in saida and "--so topicos" in saida and "quebrou" in saida


def test_so_roda_um_passo(rt, monkeypatch):
    chamados = simular(monkeypatch, rt)
    assert rt.main(["--so", "relatorio"]) == 0
    assert len(chamados) == 1 and chamados[0][-1] == "relatorio"
    chamados.clear()
    assert rt.main(["--so", "resumo"]) == 0
    assert [Path(c[1]).name for c in chamados] == ["resumo_dados.py"]


def test_notebooks_geram_e_executam_na_ordem(rt, monkeypatch):
    chamados = simular(monkeypatch, rt)
    rt.main(["--so", "notebooks"])
    esperado = [("gerar_analise.py", None), ("executar_notebook.py", "analise_descritiva"),
                ("gerar_topicos.py", None), ("executar_notebook.py", "topicos_por_periodo"),
                ("gerar_equilibrio.py", None), ("executar_notebook.py", "equilibrio_periodos"),
                ("gerar_tipos.py", None), ("executar_notebook.py", "mudanca_por_tipo"),
                ("gerar_categorias.py", None), ("executar_notebook.py", "categorias_por_periodo"),
                ("gerar_incerteza.py", None), ("executar_notebook.py", "incerteza"),
                ("gerar_material.py", None), ("executar_notebook.py", "material_do_grupo")]
    assert [(Path(c[1]).name, Path(c[2]).stem if len(c) > 2 else None) for c in chamados] == esperado
