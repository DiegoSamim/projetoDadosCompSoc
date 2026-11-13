import pytest

from hdb import acervos, config
from hdb.banco import BancoMemoria, cobre_mais_que_a_decada

JC = "https://memoria.bn.gov.br/DocReader/docreader.aspx?bib=364568_04&pasta=ano%20185&pesq=%22escravo%20fugido%22&pagfis=260"


def test_bib_do_endereco():
    assert acervos.bib_do_endereco(JC) == "364568_04"
    assert acervos.bib_do_endereco("https://x/docreader.aspx?Bib=094170&pagfis=1") == "094170"  # sem sufixo
    assert acervos.bib_do_endereco("https://x/docmulti.aspx?bib=[cache]abc") is None
    assert acervos.bib_do_endereco("https://x/docreader.aspx?pasta=ano") is None
    assert acervos.bib_do_endereco("about:blank") is None


def test_anos_do_acervo():
    assert acervos.anos_do_acervo("Diário do Rio de Janeiro (RJ) - 1821 a 1858") == (1821, 1858)
    assert acervos.anos_do_acervo("Jornal do Commercio (RJ) - 1850 a 1859") == (1850, 1859)
    assert acervos.anos_do_acervo("A Actualidade (RJ) - 1859") == (1859, 1859)
    assert acervos.anos_do_acervo("Sem anos") == (None, None)
    assert acervos.anos_do_acervo(None) == (None, None)


def test_cobre_mais_que_a_decada():
    assert cobre_mais_que_a_decada("1850 - 1859", 1850, 1859) is False
    assert cobre_mais_que_a_decada("1850 - 1859", 1821, 1858) is True
    assert cobre_mais_que_a_decada("1850 - 1859", 1855, 1865) is True
    assert cobre_mais_que_a_decada("1850 - 1859", None, None) is None


# ---------- navegador simulado ----------

class NavegadorFalso:
    def __init__(self, nomes, respostas, captcha_apos=None):
        self.nomes, self.respostas = nomes, respostas  # respostas: (posicao, sonda) -> (url, descricao) | None
        self.captcha_apos, self.consultas = captcha_apos, []

    def preparar(self, local, periodo):
        return self.nomes

    def captcha(self):
        return self.captcha_apos is not None and len({p for p, _ in self.consultas}) >= self.captcha_apos

    def consultar(self, posicao, termo):
        self.consultas.append((posicao, termo))
        resposta = self.respostas.get((posicao, termo))
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def url(bib):
    return f"https://x/docreader.aspx?bib={bib}&pagfis=1"


@pytest.fixture(autouse=True)
def sem_pausa(monkeypatch):
    monkeypatch.setattr(config, "PAUSA_CAPTURA", 0)


NOMES = ["Todos (3)", "Jornal do Commercio", "A Actualidade", "A Actualidade"]


def test_descobrir_grava_e_usa_sonda_de_reserva():
    banco = BancoMemoria()
    nav = NavegadorFalso(NOMES, {
        (1, "janeiro"): (url("364568_04"), "Jornal do Commercio (RJ) - 1850 a 1859"),
        (2, "janeiro"): None,  # sem janela
        (2, "rio"): ("https://x/docmulti.aspx?bib=[cache]x", None),  # janela sem bib
        (2, "anno"): (url("111111_01"), "A Actualidade (RJ) - 1859 a 1860"),
        (3, "janeiro"): RuntimeError("quebrou"),
    })
    assert acervos.descobrir_acervos(banco, "RJ", "1850 - 1859", navegador=nav) == 2
    por_pos = {r["posicao"]: r for r in banco.acervos_do_periodo("RJ", "1850 - 1859")}
    assert por_pos[1]["bib"] == "364568_04" and por_pos[2]["bib"] == "111111_01"
    assert por_pos[3]["bib"] is None and "quebrou" in por_pos[3]["erro"] and "sem janela" in por_pos[3]["erro"]
    assert banco.acervo("364568_04")["ano_inicio"] == 1850
    assert banco.acervo("111111_01")["nome"] == "A Actualidade (RJ) - 1859 a 1860"


def test_descobrir_retoma_e_confere_nome():
    banco = BancoMemoria()
    respostas = {(i, "janeiro"): (url(f"{i}"), f"P{i} (RJ) - 1850 a 1859") for i in (1, 2, 3)}
    acervos.descobrir_acervos(banco, "RJ", "1850 - 1859", navegador=NavegadorFalso(NOMES, respostas), limite=2)
    assert [r["posicao"] for r in banco.acervos_do_periodo("RJ", "1850 - 1859")] == [1, 2]

    nav = NavegadorFalso(NOMES, respostas)
    acervos.descobrir_acervos(banco, "RJ", "1850 - 1859", navegador=nav)
    assert nav.consultas == [(3, "janeiro")]  # 1 e 2 já gravadas

    nomes_novos = ["Todos (3)", "Jornal do Commercio", "Outro", "A Actualidade"]  # a posição 2 mudou de nome
    nav = NavegadorFalso(nomes_novos, {(2, "janeiro"): (url("999"), "Outro (RJ) - 1850 a 1859")})
    acervos.descobrir_acervos(banco, "RJ", "1850 - 1859", navegador=nav)
    assert nav.consultas == [(2, "janeiro")]
    assert {r["posicao"]: r for r in banco.acervos_do_periodo("RJ", "1850 - 1859")}[2]["bib"] == "999"


def test_descobrir_para_no_captcha(capsys):
    banco = BancoMemoria()
    respostas = {(i, "janeiro"): (url(f"{i}"), None) for i in (1, 2, 3)}
    nav = NavegadorFalso(NOMES, respostas, captcha_apos=1)
    assert acervos.descobrir_acervos(banco, "RJ", "1850 - 1859", navegador=nav) == 1
    assert "CAPTCHA" in capsys.readouterr().out


# ---------- contagens ----------

def banco_com_acervos():
    banco = BancoMemoria()
    for pos, bib, nome, ini, fim in ((1, "a", "Jornal A", 1850, 1859), (2, "b", "Diário B", 1821, 1858),
                                      (3, "c", "Gazeta C", 1855, 1859)):
        banco.garantir_acervo(bib, nome)
        banco.atualizar_acervo(bib, ano_inicio=ini, ano_fim=fim)
        banco.registrar_acervo_periodo("RJ", "1850 - 1859", pos, nome, bib=bib)
    banco.registrar_acervo_periodo("RJ", "1850 - 1859", 4, "Sem bib", erro="x")
    return banco


def test_contar_panorama(monkeypatch):
    banco = banco_com_acervos()
    banco.registrar_contagem("a", "t", 7)  # já contada: não refaz
    chamadas, totais = [], []
    contagens = {"a": 7, "b": 10, "c": 0}  # "c" não tem o termo
    monkeypatch.setattr(acervos.busca, "total_ocorrencias",
                        lambda s, bib, termo: chamadas.append((bib, termo)) or contagens[bib])
    monkeypatch.setattr(acervos, "total_de_paginas", lambda s, bib: totais.append(bib) or 100)

    acervos.contar_panorama(banco, "RJ", "1850 - 1859", ["t"], sessao=object())
    assert chamadas == [("b", "t"), ("c", "t")]
    assert totais == ["a", "b"]  # "c" tem 0 ocorrências: não calcula o total
    assert banco.contagem("a", "t") == 7 and banco.acervo("c")["total_paginas"] is None

    acervos.contar_panorama(banco, "RJ", "1850 - 1859", ["t"], sessao=object())
    assert totais == ["a", "b"]  # totais já gravados: uma vez só

    chamadas.clear()
    contagens["a"] = 8
    acervos.contar_panorama(banco, "RJ", "1850 - 1859", ["t"], recontar=True, sessao=object())
    assert len(chamadas) == 3 and banco.contagem("a", "t") == 8


def test_contar_panorama_sem_total(monkeypatch):
    banco = banco_com_acervos()
    monkeypatch.setattr(acervos.busca, "total_ocorrencias", lambda s, bib, termo: 5)
    monkeypatch.setattr(acervos, "total_de_paginas", lambda s, bib: pytest.fail("não devia chamar"))
    acervos.contar_panorama(banco, "RJ", "1850 - 1859", ["t"], sessao=object(), com_total=False)
    assert banco.contagem("b", "t") == 5


def test_ranking_e_aviso_de_decada():
    banco = banco_com_acervos()
    for bib, pag, total in (("a", 600, 6000), ("b", 900, 90000), ("c", 100, 200)):
        banco.registrar_contagem(bib, "t", pag)
        banco.atualizar_acervo(bib, total_paginas=total)

    por_paginas = acervos.ranking(banco, "RJ", "1850 - 1859", "t")
    assert [r["bib"] for r in por_paginas] == ["b", "a", "c"]
    assert por_paginas[0]["aviso"] == "cobre mais que a década" and por_paginas[1]["aviso"] == ""
    assert por_paginas[1]["anos"] == "1850-1859"

    por_pct = acervos.ranking(banco, "RJ", "1850 - 1859", "t", ordenar="percentual")
    assert [r["bib"] for r in por_pct] == ["c", "a", "b"]
    assert por_pct[0]["percentual"] == 0.5
    texto = acervos.formatar_ranking(por_pct)
    assert "cobre mais que a década" in texto and "50.00" in texto

    with pytest.raises(ValueError):
        acervos.ranking(banco, "RJ", "1850 - 1859", "t", ordenar="x")


def test_ranking_sem_total_fica_por_ultimo():
    banco = banco_com_acervos()
    banco.registrar_contagem("a", "t", 500)  # sem total_paginas
    banco.registrar_contagem("c", "t", 1)
    banco.atualizar_acervo("c", total_paginas=10)
    linhas = acervos.ranking(banco, "RJ", "1850 - 1859", "t", ordenar="percentual")
    assert [r["bib"] for r in linhas] == ["c", "a"] and linhas[1]["percentual"] is None
    assert "?" in acervos.formatar_ranking(linhas)


# ---------- importar ----------

def test_importar_csvs(tmp_path, monkeypatch):
    contagens = tmp_path / "contagens_termos.csv"
    contagens.write_text(
        "categoria,termo,bib,acervo,paginas,coletado_em\n"
        'fuga,"""escravo fugido""",364568_04,JC 1850s,671,2026-11-10T12:28:17\n'
        "curinga,escrav*,094170_01,DRJ 1821–58,3149,2026-11-10T12:30:00\n", encoding="utf-8")
    paginas = tmp_path / "paginas_por_acervo.csv"
    paginas.write_text("bib,acervo,paginas\n364568_04,JC 1850s,35000\n", encoding="utf-8")
    monkeypatch.setattr(config, "CONTAGENS_CSV", contagens)
    monkeypatch.setattr(config, "PAGINAS_CSV", paginas)

    banco = BancoMemoria()
    banco.garantir_acervo("364568_04", "Jornal do Commercio (RJ) - 1850 a 1859")
    for _ in range(2):  # repetir não duplica
        acervos.importar_contagens(banco)
        acervos.importar_paginas_por_acervo(banco)
    assert banco.contagem("364568_04", '"escravo fugido"') == 671
    assert banco.contagem("094170_01", "escrav*") == 3149
    assert banco.acervo("364568_04")["total_paginas"] == 35000
    assert banco.acervo("364568_04")["nome"] == "Jornal do Commercio (RJ) - 1850 a 1859"  # não sobrescreve
    assert banco.acervo("094170_01")["nome"] == "DRJ 1821–58"


def test_importar_sem_csvs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONTAGENS_CSV", tmp_path / "nao_existe.csv")
    monkeypatch.setattr(config, "PAGINAS_CSV", tmp_path / "nao_existe2.csv")
    banco = BancoMemoria()
    acervos.importar_contagens(banco)
    acervos.importar_paginas_por_acervo(banco)
    assert banco.contagens == {}
