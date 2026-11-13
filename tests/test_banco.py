from datetime import datetime, timedelta

import pytest

from hdb import banco as modulo_banco
from hdb import config
from hdb.banco import BancoMemoria


class Relogio:
    def __init__(self):
        self.t = datetime(2026, 1, 1, 12, 0)

    def __call__(self):
        return self.t

    def avancar(self, minutos):
        self.t += timedelta(minutes=minutos)


OCR = {"texto": "texto " * 50, "confianca": 91.5, "colunas": 2, "motor": "tesseract-5 por psm4", "segundos": 7.0}


def linha(bib, pagfis, termo="fugido", posicao=1):
    return {"bib": bib, "acervo": f"Acervo {bib}", "termo": termo, "ocorrencia": posicao,
            "total_ocorrencias": 9, "ano": "1850", "edicao": "00012", "pagina": "4",
            "pagina_fisica": str(pagfis), "link": f"https://x/{bib}/{pagfis}"}


@pytest.fixture
def relogio():
    return Relogio()


@pytest.fixture
def banco(relogio):
    b = BancoMemoria(agora=relogio)
    for i, (bib, pagfis) in enumerate([("b", 5), ("a", 20), ("a", 3), ("a", 10)], start=1):
        b.registrar_ocorrencia(linha(bib, pagfis, posicao=i))
    return b


def paginas(reservadas):
    return [(p["bib"], p["pagina_fisica"]) for p in reservadas]


def test_registrar_ocorrencia_nao_duplica_nem_sobrescreve(banco):
    banco.reservar("ana", 1)
    banco.registrar_ocorrencia(linha("a", 3, posicao=1))  # mesma página, ocorrência nova
    banco.registrar_ocorrencia(linha("a", 3, posicao=1))  # repetida
    assert len(banco.paginas) == 4
    assert banco.contar_ocorrencias("a", "fugido") == 4  # 3 originais + a nova; a repetida não conta
    assert banco.pagina("a", 3)["status"] == "reservada"  # o upsert não zera o status


def test_contar_ocorrencias_por_bib_e_termo(banco):
    assert banco.contar_ocorrencias("a", "fugido") == 3
    assert banco.contar_ocorrencias("b", "fugido") == 1
    assert banco.contar_ocorrencias("a", "outro") == 0


def test_reserva_na_ordem_do_acervo_e_sem_repeticao(banco):
    ana = banco.reservar("ana", 2)
    bia = banco.reservar("bia", 10)
    assert paginas(ana) == [("a", 3), ("a", 10)]  # pagina_fisica numérica, não por texto
    assert paginas(bia) == [("a", 20), ("b", 5)]
    assert banco.reservar("ana", 10) == []


def test_filtros_de_bib_e_termo(banco):
    banco.registrar_ocorrencia(linha("a", 10, termo="escravo", posicao=1))
    assert paginas(banco.reservar("ana", 10, bib="b")) == [("b", 5)]
    assert paginas(banco.reservar("ana", 10, termo="escravo")) == [("a", 10)]


def test_aleatorio_devolve_as_mesmas_paginas(banco):
    assert sorted(paginas(banco.reservar("ana", 10, aleatorio=True))) == [("a", 3), ("a", 10), ("a", 20), ("b", 5)]


def test_erro_volta_para_a_fila_ate_o_limite(banco):
    for tentativa in range(1, config.MAX_TENTATIVAS + 1):
        [p] = banco.reservar("ana", 1)
        assert (p["bib"], p["pagina_fisica"]) == ("a", 3)  # a de erro volta antes das outras
        banco.registrar_erro(p["id"], "ana", "captura", "falhou", 1.0, 0)
        assert banco.paginas[p["id"]]["tentativas"] == tentativa
    [seguinte] = banco.reservar("ana", 1)
    assert (seguinte["bib"], seguinte["pagina_fisica"]) == ("a", 10)  # esgotou: não volta mais
    assert banco.paginas[p["id"]]["status"] == "erro"
    assert banco.paginas[p["id"]]["ultimo_erro"] == "falhou"


def test_erro_de_ocr_nao_volta_para_a_fila(banco):
    [p] = banco.reservar("ana", 1)
    banco.registrar_erro(p["id"], "ana", "ocr", "texto curto", 1.0, 1)
    assert ("a", 3) not in paginas(banco.reservar("ana", 10))
    assert banco.paginas[p["id"]]["etapa_erro"] == "ocr"


def test_sucesso_limpa_etapa_do_erro(banco):
    [p] = banco.reservar("ana", 1)
    banco.registrar_erro(p["id"], "ana", "captura", "x", 1.0, 0)
    [p] = banco.reservar("ana", 1)
    banco.registrar_sucesso(p["id"], "ana", 1, 1, 1, OCR, 1.0, 0)
    assert banco.paginas[p["id"]]["etapa_erro"] is None


def test_lote_seguinte_nao_repete_pagina_excluida(banco):
    [a] = banco.reservar("ana", 1)
    banco.registrar_erro(a["id"], "ana", "captura", "x", 1.0, 0)  # voltaria à fila...
    seguinte = banco.reservar("ana", 1, excluir=[a["id"]])
    assert paginas(seguinte) == [("a", 10)]  # ...mas esta execução já a tentou


def test_reserva_expirada_volta(banco, relogio):
    assert len(banco.reservar("ana", 4)) == 4
    relogio.avancar(config.RESERVA_MINUTOS - 1)
    assert banco.reservar("bia", 4) == []
    relogio.avancar(2)
    assert len(banco.reservar("bia", 4)) == 4
    assert all(p["reservada_por"] == "bia" for p in banco.paginas.values())


def test_sucesso_limpa_reserva_e_grava_texto(banco):
    [p] = banco.reservar("ana", 1)
    banco.registrar_sucesso(p["id"], "ana", 5800, 8940, 3_000_000, OCR, 12.0, 1)
    pagina = banco.paginas[p["id"]]
    assert (pagina["status"], pagina["reservada_por"], pagina["reservada_em"]) == ("ok", None, None)
    assert (pagina["largura"], pagina["altura"], pagina["bytes"]) == (5800, 8940, 3_000_000)
    assert banco.leituras[(p["id"], OCR["motor"])]["confianca"] == 91.5
    assert banco.tentativas[-1]["status"] == "ok" and banco.tentativas[-1]["captchas"] == 1
    assert [x["pagina_fisica"] for x in banco.reservar("ana", 10)] == [10, 20, 5]  # a ok não volta


def test_sucesso_repetido_atualiza_o_texto(banco):
    [p] = banco.reservar("ana", 1)
    banco.registrar_sucesso(p["id"], "ana", 1, 1, 1, OCR, 1.0, 0)
    banco.registrar_sucesso(p["id"], "ana", 1, 1, 1, {**OCR, "texto": "novo"}, 1.0, 0)
    assert len(banco.leituras) == 1 and banco.leituras[(p["id"], OCR["motor"])]["texto"] == "novo"


def test_liberar_reservas_so_de_quem_pediu(banco):
    banco.reservar("ana", 2)
    banco.reservar("bia", 1)
    assert banco.liberar_reservas("ana") == 2
    assert sorted(paginas(banco.reservar("cris", 10))) == [("a", 3), ("a", 10), ("b", 5)]
    assert banco.pagina("a", 20)["status"] == "reservada"  # a de bia continua dela


def test_pagina_inexistente():
    assert BancoMemoria().pagina("x", 1) is None


def test_status(banco):
    a, b = banco.reservar("ana", 2)
    banco.registrar_sucesso(a["id"], "ana", 1, 1, 1, OCR, 1.0, 2)
    banco.registrar_erro(b["id"], "ana", "ocr", "texto curto", 1.0, 0)
    s = banco.status()
    assert s["por_status"] == {"ok": 1, "erro": 1, "pendente": 2}
    assert s["por_acervo"]["a"] == {"ok": 1, "erro": 1, "pendente": 1}
    assert s["por_termo"]["fugido"]["pendente"] == 2
    assert s["ultimos_erros"][0]["etapa"] == "ocr" and s["ultimos_erros"][0]["pagina_fisica"] == 10
    assert s["paginas_por_captcha"] == 0.5  # 1 ok para 2 CAPTCHAs


def test_status_sem_captcha_registrado():
    assert BancoMemoria().status()["paginas_por_captcha"] is None


def test_supabase_exige_credenciais(monkeypatch, tmp_path):
    monkeypatch.setattr(modulo_banco.config, "RAIZ", tmp_path)  # sem .env
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_URL e SUPABASE_SECRET_KEY"):
        modulo_banco.BancoSupabase()


def test_reprocesso_recupera_pagina_em_erro(banco):
    p = banco.reservar("ana", 1)[0]
    banco.registrar_erro(p["id"], "ana", "ocr", "texto curto", 2.0, 0)
    banco.registrar_reprocesso(p["id"], "bia", 5800, 8940, 1234, OCR)
    pagina = banco.paginas[p["id"]]
    assert pagina["status"] == "ok" and pagina["ultimo_erro"] is None and pagina["etapa_erro"] is None
    assert (pagina["largura"], pagina["altura"], pagina["bytes"]) == (5800, 8940, 1234)
    assert pagina["capturada_em"] is not None
    ultima = banco.tentativas[-1]
    assert (ultima["quem"], ultima["status"], ultima["etapa"], ultima["captchas"]) == ("bia", "ok", "ocr", 0)


def test_reprocesso_de_pagina_ok_so_muda_o_texto(banco):
    p = banco.reservar("ana", 1)[0]
    banco.registrar_sucesso(p["id"], "ana", 100, 200, 300, OCR, 9.0, 1)
    antes = dict(banco.paginas[p["id"]])
    banco.registrar_reprocesso(p["id"], "bia", 1, 2, 3, {**OCR, "motor": "outro"})
    assert banco.paginas[p["id"]] == antes
    assert len(banco.tentativas) == 1


def test_dois_motores_coexistem_e_textos_devolve_os_dois(banco, relogio):
    p = banco.reservar("ana", 1)[0]
    banco.registrar_sucesso(p["id"], "ana", 100, 200, 300, OCR, 9.0, 1)
    relogio.avancar(5)
    banco.registrar_reprocesso(p["id"], "bia", 1, 2, 3, {**OCR, "motor": "novo", "confianca": 70.0})
    textos = banco.textos(p["id"])
    assert {t["motor"] for t in textos} == {OCR["motor"], "novo"}
    assert set(textos[0]) == {"motor", "confianca", "texto", "criado_em"}
    assert max(textos, key=lambda t: t["criado_em"])["motor"] == "novo"
    relogio.avancar(5)
    banco.registrar_reprocesso(p["id"], "bia", 1, 2, 3, {**OCR, "confianca": 10.0})  # mesmo motor: atualiza
    textos = {t["motor"]: t for t in banco.textos(p["id"])}
    assert len(textos) == 2 and textos[OCR["motor"]]["criado_em"] == relogio.t
    assert banco.textos(9999) == []


def anuncio(ordem, texto="vende-se um escravo"):
    return {"ordem": ordem, "coluna": 1, "titulo": None, "abertura": "VENDE-SE", "texto_bruto": texto,
            "texto": texto, "confianca": 80.0, "x0": 1, "y0": 2, "x1": 3, "y1": 4, "n_linhas": 1, "largo": False}


def test_registrar_anuncios_devolve_quantos_e_lista_em_ordem(banco):
    assert banco.registrar_anuncios(1, "v1", [anuncio(2), anuncio(1)]) == 2
    achados = banco.anuncios(1)
    assert [a["ordem"] for a in achados] == [1, 2]
    assert all(a["pagina_id"] == 1 and a["versao"] == "v1" for a in achados)


def test_registrar_anuncios_substitui_a_mesma_versao_e_mantem_as_outras(banco):
    banco.registrar_anuncios(1, "v1", [anuncio(1), anuncio(2)])
    banco.registrar_anuncios(1, "v2", [anuncio(1, "outra versao")])
    banco.registrar_anuncios(1, "v1", [anuncio(1, "refeito")])
    assert [a["texto"] for a in banco.anuncios(1, "v1")] == ["refeito"]
    assert [a["texto"] for a in banco.anuncios(1, "v2")] == ["outra versao"]
    assert len(banco.anuncios(1)) == 2


def test_anuncios_sao_por_pagina(banco):
    banco.registrar_anuncios(1, "v1", [anuncio(1)])
    assert banco.anuncios(2) == [] and banco.anuncios(1, "v9") == []


def test_anuncios_para_campos_lista_so_a_versao_com_id(banco):
    banco.registrar_anuncios(1, "v1", [anuncio(1, "a")])
    banco.registrar_anuncios(2, "v2", [anuncio(1, "b"), anuncio(2, "c")])
    achados = banco.anuncios_para_campos("v2")
    assert [a["texto"] for a in achados] == ["b", "c"]
    assert set(achados[0]) == {"id", "titulo", "abertura", "texto"} and achados[0]["id"] != achados[1]["id"]
    assert banco.anuncios_para_campos("v9") == []


def test_registrar_campos_faz_upsert_e_versoes_coexistem(banco):
    assert banco.registrar_campos("c1", [{"anuncio_id": 1, "tipo": "venda"}, {"anuncio_id": 2, "tipo": "fuga"}]) == 2
    banco.registrar_campos("c1", [{"anuncio_id": 1, "tipo": "outro"}])
    banco.registrar_campos("c2", [{"anuncio_id": 1, "tipo": "compra"}])
    assert banco.campos[(1, "c1")]["tipo"] == "outro" and banco.campos[(2, "c1")]["tipo"] == "fuga"
    assert banco.campos[(1, "c2")]["tipo"] == "compra" and len(banco.campos) == 3
