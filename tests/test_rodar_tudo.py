import importlib.util
import subprocess
from pathlib import Path

import pytest

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts" / "rodar_tudo.py"
ORDEM = ["campos", "corpus", "corpus_i", "topicos", "topicos_i", "estabilidade", "relatorio", "notebooks"]


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
    assert [c[3] for c in chamados] == ["campos", "corpus", "corpus", "topicos", "topicos", "relatorio"]
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


def test_notebooks_geram_e_executam(rt, monkeypatch):
    chamados = simular(monkeypatch, rt)
    rt.main(["--so", "notebooks"])
    assert [Path(c[1]).name for c in chamados] == ["gerar_analise.py", "gerar_topicos.py",
                                                    "executar_notebook.py", "executar_notebook.py"]
