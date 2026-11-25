import importlib.util
from pathlib import Path

import pytest

from hdb.banco import BancoMemoria

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts" / "amostra.py"


@pytest.fixture(scope="module")
def amostra():
    spec = importlib.util.spec_from_file_location("amostra", ARQUIVO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_celulas_da_cobertura(amostra):
    cobertura = amostra.celulas(cobertura=True)
    assert cobertura == amostra.COBERTURA and len(cobertura) == 3
    assert [c[4] for c in cobertura] == ['"fugio o escravo"', '"preto fugido"', '"fugio a escrava"']  # frases pequenas
    assert all(c[2] == "364568_07" for c in cobertura) and amostra.ANO_MIN_COBERTURA == 1887
    assert amostra.celulas(pessoa=2, cobertura=True) == []  # a célula é de 1871–1888, que é da pessoa 1
    assert amostra.celulas() == amostra.AMOSTRA


def test_listagem_do_complemento_e_da_cobertura(amostra):
    assert amostra.LISTAR_COMPLEMENTO == 450 and amostra.LISTAR_EXTRAS == 60 and amostra.LISTAR_COBERTURA is None


def test_situacao_da_cobertura_mostra_os_anos_ok(amostra, capsys):
    b = BancoMemoria()
    for i, ano in enumerate([1880, 1880, 1886], start=1):
        b.registrar_ocorrencia({"bib": "364568_07", "acervo": "x", "termo": '"fugio o escravo"', "ocorrencia": i,
                                "total_ocorrencias": 3, "ano": str(ano), "edicao": "1", "pagina": "1",
                                "pagina_fisica": str(i), "link": "l"})
        b.paginas[i]["status"] = "ok"
    amostra.situacao(b, cobertura=True)
    saida = capsys.readouterr().out
    meta = sum(c[-1] for c in amostra.COBERTURA)
    assert "anos ok: 1880×2, 1886×1" in saida and f"Capturadas: 3 de {meta} páginas da cobertura" in saida


def test_capturar_da_cobertura_pede_so_de_1887_em_diante(amostra, monkeypatch):
    chamadas = []
    import hdb.captura as cap
    monkeypatch.setattr(cap, "capturar", lambda banco, quem, **kw: chamadas.append(kw) or False)
    amostra.capturar(BancoMemoria(), "ana", "terminal", cobertura=True)
    assert chamadas and all(c["ano_min"] == 1887 and c["equilibrar"] for c in chamadas)
    chamadas.clear()
    amostra.capturar(BancoMemoria(), "ana", "terminal", complemento=True)
    assert all(c["ano_min"] is None for c in chamadas)
