from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from hdb import busca
from hdb.armazenamento import ler_csv_parcial
from hdb.banco import BancoMemoria

FIXTURES = Path(__file__).parent / "fixtures"


def soup_de(nome):
    return BeautifulSoup((FIXTURES / nome).read_text(encoding="utf-8"), "lxml")


def test_ler_ocorrencia_primeira():
    r = busca.ler_ocorrencia(soup_de("docreader_706744_fugiu_1.html"), "706744")
    assert r["acervo"] == "Imperio do Brasil: Diario Fluminense (RJ) - 1825 a 1831"
    assert r["termo"] == "fugiu"
    assert r["total_ocorrencias"] == 5
    assert (r["ano"], r["edicao"]) == ("1826", "00007")
    assert r["pagina_fisica"] == "1507"
    assert r["link"] == "https://memoria.bn.gov.br/docreader/706744/1507"


def test_ocorrencia_e_controlada_por_quem_chama():
    # O rótulo do servidor diz "2/5", mas o número gravado é o que o chamador informa.
    soup = soup_de("docreader_706744_fugiu_2.html")
    assert busca.ler_ocorrencia(soup, "706744", ocorrencia=7)["ocorrencia"] == 7


def test_total_zero_sem_rotulo():
    assert busca.total_do_rotulo(BeautifulSoup("<html></html>", "lxml")) == 0


@pytest.mark.parametrize(
    "decada,esperado",
    [(1830, "1831–1850"), (1840, "1831–1850"), (1850, "1850–1871"), (1860, "1850–1871"),
     (1870, "1871–1888"), (1880, "1871–1888")],
)
def test_periodo_legal(decada, esperado):
    assert busca.periodo_legal(decada).startswith(esperado)


def test_ler_csv_parcial(tmp_path):
    assert ler_csv_parcial(tmp_path / "nao_existe.csv") == []
    csv = tmp_path / "x.csv"
    csv.write_text("ocorrencia,total_ocorrencias,ano\n1,5,1826\n2,5,1827\n", encoding="utf-8")
    linhas = ler_csv_parcial(csv)
    assert [l["ocorrencia"] for l in linhas] == [1, 2]
    assert linhas[0]["total_ocorrencias"] == 5 and linhas[0]["ano"] == "1826"


class ServidorFalso:
    """Imita o DocReader: guarda a posição e conta quantas vezes avançou."""

    def __init__(self, total):
        self.total, self.pos, self.avancos = total, 1, 0

    def abrir(self, sessao, bib, termo):
        self.pos = 1
        return "url", self.pagina()

    def avancar(self, sessao, url, soup):
        self.pos += 1
        self.avancos += 1
        return self.pagina()

    def pagina(self):
        # O rótulo "atual/total" é mentira de propósito: só o total deve ser usado.
        return BeautifulSoup(
            f'<span id="OcorNroLbl">1/{self.total}</span>'
            f'<span id="PastaTxt" title="Ano 18{self.pos:02d}\\Edição {self.pos:05d}"></span>'
            f'<input id="hPagFis" value="{self.pos}"/>',
            "lxml",
        )


@pytest.fixture
def servidor(monkeypatch):
    s = ServidorFalso(total=5)
    monkeypatch.setattr(busca, "abrir_busca", s.abrir)
    monkeypatch.setattr(busca, "proxima_ocorrencia", s.avancar)
    return s


def test_coletar_respeita_limite(servidor):
    banco = BancoMemoria()
    assert busca.coletar_ocorrencias(None, "x", "y", banco, limite=3) == (3, 5)
    assert sorted(banco.ocorrencias) == [("x", "y", 1), ("x", "y", 2), ("x", "y", 3)]
    assert [p["pagina_fisica"] for p in banco.paginas.values()] == [1, 2, 3]
    assert all(p["status"] == "pendente" for p in banco.paginas.values())


def test_coletar_retoma_de_onde_parou(servidor):
    banco = BancoMemoria()
    busca.coletar_ocorrencias(None, "x", "y", banco, limite=2)
    servidor.avancos = 0
    assert busca.coletar_ocorrencias(None, "x", "y", banco) == (5, 5)  # completa até 5

    assert banco.contar_ocorrencias("x", "y") == 5  # nada gravado em duplicidade
    assert servidor.pos == 5  # o servidor foi reposicionado antes de continuar
    assert servidor.avancos == 1 + 3  # 1 para reposicionar na 2ª + 3 novas


def test_coletar_nao_mexe_em_pagina_existente(servidor):
    banco = BancoMemoria()
    busca.coletar_ocorrencias(None, "x", "y", banco, limite=1)
    banco.registrar_erro(1, "ana", "ocr", "falhou", 1.0, 0)
    busca.coletar_ocorrencias(None, "x", "z", banco, limite=1)  # outro termo, mesma página
    assert len(banco.paginas) == 1
    assert banco.paginas[1]["status"] == "erro"


def test_coletar_sem_resultados(monkeypatch):
    monkeypatch.setattr(busca, "abrir_busca", lambda *a: ("u", BeautifulSoup("<p></p>", "lxml")))
    assert busca.coletar_ocorrencias(None, "x", "y", BancoMemoria()) == (0, 0)
