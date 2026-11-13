import json
import sys
import types
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from hdb import captura, config, ocr
from hdb.banco import BancoMemoria

TEXTO = "Fugio o escravo Joaquim, crioulo. " * 10  # passa do mínimo de caracteres


def linha(bib, pagfis, termo="fugido", posicao=1):
    return {"bib": bib, "acervo": "A", "termo": termo, "ocorrencia": posicao, "total_ocorrencias": 3,
            "ano": "1850", "edicao": "00012", "pagina": "4", "pagina_fisica": str(pagfis),
            "link": f"https://x/{bib}/{pagfis}"}


def ocr_falso(caminho):
    """OCR sem Tesseract: a página 13 vem quase vazia; a 14 quebra."""
    pagfis = captura.pagina_do_tmp(caminho)[1]
    if pagfis == 14:
        raise ValueError("imagem corrompida")
    texto = "ruído" if pagfis == 13 else TEXTO
    return {"texto": texto, "confianca": 88.0, "colunas": 2, "motor": "falso", "segundos": 1.0}


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Diretórios temporários, OCR falso em threads, tempo de espera zero."""
    monkeypatch.setattr(config, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(config, "IMAGENS_DIR", tmp_path / "imagens")
    monkeypatch.setattr(config, "OCORRENCIAS_DIR", tmp_path / "ocorrencias")
    monkeypatch.setattr(config, "CAPTURA_DIR", tmp_path / "captura")
    monkeypatch.setattr(config, "FALHAS_OCR_DIR", tmp_path / "falhas_ocr")
    monkeypatch.setattr(config, "CONTAGENS_CSV", tmp_path / "contagens_termos.csv")
    monkeypatch.setattr(config, "PAGINAS_CSV", tmp_path / "paginas_por_acervo.csv")
    monkeypatch.setattr(config, "PAUSA_CAPTURA", 0)
    monkeypatch.setattr(captura, "_criar_executor", lambda workers: ThreadPoolExecutor(workers))
    monkeypatch.setattr(ocr, "extrair_texto", ocr_falso)
    return tmp_path


class ContextoFalso:
    def __init__(self):
        self.fechado = False
        self.pages = []

    def new_page(self):
        return object()

    def close(self):
        self.fechado = True


def navegador_falso(monkeypatch, quebrar_em=None, interromper_em=None):
    """Troca o Playwright por um falso e `_capturar_pagina` por uma que só grava um arquivo."""
    contexto = ContextoFalso()
    chromium = types.SimpleNamespace(launch_persistent_context=lambda *a, **k: contexto)
    fake = types.ModuleType("playwright.sync_api")

    class SyncPlaywright:
        def __enter__(self):
            return types.SimpleNamespace(chromium=chromium)

        def __exit__(self, *a):
            return False

    fake.sync_playwright = SyncPlaywright
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake)
    chamadas = []

    def capturar_pagina(page, context, pagina, modo, tamanho, abrir):
        chamadas.append((pagina["pagina_fisica"], abrir))
        if pagina["pagina_fisica"] == interromper_em:
            raise KeyboardInterrupt
        if pagina["pagina_fisica"] == quebrar_em:
            raise TimeoutError("a imagem não apareceu em 60 s")
        destino = captura.caminho_tmp(pagina["bib"], pagina["pagina_fisica"])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"imagem")
        return 1, 5800, 8940, 6

    monkeypatch.setattr(captura, "_capturar_pagina", capturar_pagina)
    return contexto, chamadas


def banco_com(paginas, bib="1"):
    banco = BancoMemoria()
    for i, pagfis in enumerate(paginas, start=1):
        banco.registrar_ocorrencia(linha(bib, pagfis, posicao=i))
    return banco


def test_caminho_tmp_e_pagina_do_tmp(ambiente):
    caminho = captura.caminho_tmp("364568_04", "40")
    assert caminho == config.TMP_DIR / "364568_04_00040.jpg"
    assert captura.pagina_do_tmp(caminho) == ("364568_04", 40)
    assert captura.pagina_do_tmp("706744_01507.jpg") == ("706744", 1507)


def test_captura_grava_texto_apaga_tmp_e_registra_falhas(ambiente, monkeypatch):
    contexto, chamadas = navegador_falso(monkeypatch, quebrar_em=12)
    banco = banco_com([10, 11, 12, 13, 14])
    captura.capturar(banco, "ana", max_paginas=10)

    status = {p["pagina_fisica"]: p["status"] for p in banco.paginas.values()}
    assert status == {10: "ok", 11: "ok", 12: "erro", 13: "erro", 14: "erro"}
    etapas = {banco.paginas[t["pagina_id"]]["pagina_fisica"]: t["etapa"] for t in banco.tentativas}
    assert etapas == {10: "banco", 11: "banco", 12: "captura", 13: "ocr", 14: "ocr"}
    erros = {p["pagina_fisica"]: p["ultimo_erro"] for p in banco.paginas.values()}
    assert "caracteres" in erros[13] and "corrompida" in erros[14] and "60 s" in erros[12]
    assert len(banco.leituras) == 2
    assert list(config.TMP_DIR.glob("*.jpg")) == []
    # OCR que falhou não apaga a imagem: ela vai para data/falhas_ocr/
    assert sorted(p.name for p in config.FALHAS_OCR_DIR.glob("*/*.jpg")) == ["1_00013.jpg", "1_00014.jpg"]
    assert [p["reservada_por"] for p in banco.paginas.values()] == [None] * 5
    assert contexto.fechado
    # goto só no primeiro acervo e de novo depois do erro de captura
    assert chamadas == [(10, True), (11, False), (12, False), (13, True), (14, False)]


def test_erro_de_ocr_nao_gera_nova_captura(ambiente, monkeypatch):
    _, chamadas = navegador_falso(monkeypatch, quebrar_em=12)
    banco = banco_com([12, 13])
    captura.capturar(banco, "ana")
    captura.capturar(banco, "ana")
    assert [c[0] for c in chamadas] == [12, 13, 12]  # só a falha de captura é refeita; a 13 (OCR) não


def test_lotes_nao_repetem_pagina_que_falhou(ambiente, monkeypatch):
    monkeypatch.setattr(config, "LOTE_RESERVA", 1)
    _, chamadas = navegador_falso(monkeypatch, quebrar_em=1)
    captura.capturar(banco_com([1, 2, 3]), "ana", max_paginas=3)
    assert [c[0] for c in chamadas] == [1, 2, 3]


def test_processos_de_ocr_ignoram_sigint(monkeypatch):
    chamadas = []
    monkeypatch.setattr(captura.signal, "signal", lambda *a: chamadas.append(a))
    captura._ignorar_sigint()
    assert chamadas == [(captura.signal.SIGINT, captura.signal.SIG_IGN)]
    executor = captura._criar_executor(1)  # o executor real usa essa função como initializer
    assert executor._initializer is captura._ignorar_sigint
    executor.shutdown()


def test_captura_guarda_imagem_se_pedido(ambiente, monkeypatch):
    navegador_falso(monkeypatch)
    captura.capturar(banco_com([10]), "ana", guardar=ambiente / "copia")
    assert (ambiente / "copia" / "1" / "1_00010.jpg").exists()
    assert list(config.TMP_DIR.glob("*.jpg")) == []


def test_respeita_max_paginas_e_nao_repete_paginas_ok(ambiente, monkeypatch):
    _, chamadas = navegador_falso(monkeypatch)
    banco = banco_com([1, 2, 3, 4])
    captura.capturar(banco, "ana", max_paginas=2)
    captura.capturar(banco, "bia", max_paginas=10)
    assert [c[0] for c in chamadas] == [1, 2, 3, 4]  # cada página uma vez só
    assert {p["status"] for p in banco.paginas.values()} == {"ok"}
    captura.capturar(banco, "ana")
    assert len(chamadas) == 4  # tudo ok: nada a capturar


def test_ctrl_c_libera_as_reservas(ambiente, monkeypatch):
    contexto, _ = navegador_falso(monkeypatch, interromper_em=2)
    banco = banco_com([1, 2, 3])
    captura.capturar(banco, "ana")
    assert contexto.fechado
    assert banco.pagina("1", 1)["status"] == "ok"
    assert banco.pagina("1", 2)["status"] == "pendente" and banco.pagina("1", 3)["status"] == "pendente"


def test_entrada_encerrada_no_captcha_nao_gasta_tentativa(ambiente, monkeypatch):
    navegador_falso(monkeypatch)

    def sem_entrada(*a):
        raise EOFError

    monkeypatch.setattr(captura, "_capturar_pagina", sem_entrada)
    banco = banco_com([1])
    captura.capturar(banco, "ana")
    assert banco.paginas[1]["status"] == "pendente" and banco.paginas[1]["tentativas"] == 0


def test_imagem_orfa_e_processada_sem_capturar(ambiente, monkeypatch):
    _, chamadas = navegador_falso(monkeypatch)
    banco = banco_com([10, 11])
    config.TMP_DIR.mkdir(parents=True)
    Image.new("RGB", (40, 60)).save(captura.caminho_tmp("1", 10))  # sobrou de uma execução que caiu
    captura.caminho_tmp("1", 99).write_bytes(b"x")  # página que o banco não conhece
    captura.capturar(banco, "ana")
    assert [c[0] for c in chamadas] == [11]  # a 10 veio da imagem órfã
    assert banco.pagina("1", 10)["status"] == "ok"
    assert (banco.paginas[1]["largura"], banco.paginas[1]["altura"]) == (40, 60)
    assert [p.name for p in config.TMP_DIR.glob("*.jpg")] == ["1_00099.jpg"]


def test_orfa_de_pagina_ja_ok_e_apagada(ambiente, monkeypatch):
    navegador_falso(monkeypatch)
    banco = banco_com([10])
    [p] = banco.reservar("ana", 1)
    banco.registrar_sucesso(p["id"], "ana", 1, 1, 1, ocr_falso(captura.caminho_tmp("1", 10)), 1.0, 0)
    config.TMP_DIR.mkdir(parents=True)
    captura.caminho_tmp("1", 10).write_bytes(b"x")
    captura.capturar(banco, "ana")
    assert list(config.TMP_DIR.glob("*.jpg")) == []


def test_banco_fora_do_ar_mantem_a_imagem(ambiente, monkeypatch, capsys):
    navegador_falso(monkeypatch)
    banco = banco_com([10])

    def quebra(*a, **k):
        raise ConnectionError("sem rede")

    monkeypatch.setattr(banco, "registrar_sucesso", quebra)
    captura.capturar(banco, "ana")
    assert captura.caminho_tmp("1", 10).exists()  # será reaproveitada na próxima execução
    assert "falha ao gravar no banco" in capsys.readouterr().out


def test_importar_existentes(ambiente):
    config.OCORRENCIAS_DIR.mkdir()
    (config.OCORRENCIAS_DIR / "1_fugiu.csv").write_text(
        "bib,acervo,termo,ocorrencia,total_ocorrencias,ano,edicao,pagina,pagina_fisica,link\n"
        "1,A,fugiu,1,2,1826,00007,328,10,https://x/1/10\n"
        "1,A,fugiu,2,2,1827,00009,407,11,https://x/1/11\n", encoding="utf-8")
    pasta = config.IMAGENS_DIR / "1"
    pasta.mkdir(parents=True)
    (pasta / "1_00010.jpg").write_bytes(b"imagem")
    (pasta / "1_00010.json").write_text(json.dumps(
        {"bib": "1", "acervo": "A", "pagina_fisica": "10", "ano": "1826", "edicao": "00007",
         "pagina": "328", "link": "https://x/1/10", "largura": 5800, "altura": 8940, "bytes": 6}))
    (pasta / "1_00011.jpg").write_bytes(b"sem json")  # ignorada

    banco = BancoMemoria()
    captura.importar_existentes(banco, "ana")
    captura.importar_existentes(banco, "ana")  # repetir não duplica nem refaz o OCR

    assert banco.contar_ocorrencias("1", "fugiu") == 2
    assert banco.pagina("1", 10)["status"] == "ok" and banco.pagina("1", 11)["status"] == "pendente"
    assert len(banco.leituras) == 1 and len(banco.tentativas) == 1
    assert (pasta / "1_00010.jpg").exists()  # a imagem original continua lá


def test_fracao_palavras_plausiveis():
    assert captura.fracao_palavras_plausiveis("") == 0.0
    # "Fugio", "escravo," e "bem-feito" contam; "de" é curta, "x9" tem número, "|||" não tem letras
    assert captura.fracao_palavras_plausiveis("Fugio escravo, bem-feito de x9 |||") == 3 / 6
    assert captura.fracao_palavras_plausiveis("Ações óbvias") == 1.0


def imagem(pasta, bib, pagfis, tamanho=(30, 20)):
    destino = pasta / bib / f"{bib}_{pagfis:05d}.jpg"
    destino.parent.mkdir(parents=True, exist_ok=True)
    Image.new("L", tamanho).save(destino)
    return destino


def ocr_reprocesso(caminho):
    """Página 2 rende texto curto; as demais, TEXTO com confiança 60."""
    pagfis = captura.pagina_do_tmp(caminho)[1]
    texto = "curto" if pagfis == 2 else TEXTO
    return {"texto": texto, "confianca": 60.0, "colunas": 1, "motor": "novo", "segundos": 1.0, "largura": 3000}


def test_reprocessar_compara_grava_e_ignora(ambiente, monkeypatch, capsys):
    monkeypatch.setattr(ocr, "extrair_texto", ocr_reprocesso)
    banco = banco_com([1, 2, 3])
    anterior = {"texto": "ruído " * 50, "confianca": 44.0, "colunas": 1, "motor": "velho", "segundos": 1.0}
    p1, p3 = banco.pagina("1", 1), banco.pagina("1", 3)
    banco.registrar_sucesso(p1["id"], "ana", 1, 1, 1, anterior, 1.0, 0)  # ok, com leitura antiga
    banco.registrar_erro(p3["id"], "ana", "ocr", "texto curto", 1.0, 0)  # em erro, sem leitura

    pasta_a, pasta_b = ambiente / "a", ambiente / "b"
    for pagfis in (1, 2, 3):
        imagem(pasta_a, "1", pagfis)
    imagem(pasta_b, "1", 1, tamanho=(40, 40))  # duplicata: vale a primeira
    imagem(pasta_b, "1", 99)  # página desconhecida
    captura.reprocessar(banco, "bia", [pasta_a, pasta_b], workers=2)

    saida = capsys.readouterr().out
    assert "1 p.1: conf 44.0 -> 60.0" in saida and "palavras plausíveis 100% -> 80%" in saida
    assert "1 p.3: conf 60.0" in saida and "sem leitura anterior" in saida
    assert "texto com 5 caracteres" in saida and "não gravado" in saida
    assert "1_00099.jpg: página desconhecida" in saida and "página repetida" in saida
    assert "1 melhoraram em confiança, 0 pioraram, 1 recuperadas" in saida
    assert "confiança média 44.0 -> 60.0" in saida

    assert {t["motor"] for t in banco.textos(p1["id"])} == {"velho", "novo"}
    assert banco.paginas[p1["id"]]["largura"] == 1 and banco.paginas[p1["id"]]["status"] == "ok"  # já ok: intacta
    assert banco.paginas[p3["id"]]["status"] == "ok" and banco.paginas[p3["id"]]["largura"] == 30
    assert banco.pagina("1", 2)["status"] == "pendente" and banco.textos(banco.pagina("1", 2)["id"]) == []
    assert (pasta_a / "1" / "1_00001.jpg").exists() and (pasta_b / "1" / "1_00099.jpg").exists()


def test_reprocessar_respeita_limite(ambiente, monkeypatch):
    monkeypatch.setattr(ocr, "extrair_texto", ocr_reprocesso)
    banco = banco_com([3, 4, 5])
    for pagfis in (3, 4, 5):
        imagem(ambiente / "a", "1", pagfis)
    captura.reprocessar(banco, "bia", [ambiente / "a"], workers=1, limite=2)
    assert len(banco.leituras) == 2


# ---------- anúncios ----------

def _dados_de_palavras():
    linhas = ["Vende-se uma casa grande na rua", "do Ouvidor com quintal e jardim"]
    palavras = [{"t": t, "x": 100 + 60 * i, "y": 500 + 20 * j, "w": 50, "h": 15, "c": 90.0, "b": 1, "p": 1, "l": j + 1}
                for j, linha in enumerate(linhas) for i, t in enumerate(linha.split())]
    return {"largura": 1000, "altura": 1000, "palavras": palavras, "motor": "falso", "segundos": 0.1}


def test_palavras_da_imagem_usa_o_cache_em_disco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OCR_PALAVRAS_DIR", tmp_path / "cache")
    chamadas = []
    monkeypatch.setattr(captura.ocr, "ler_palavras", lambda caminho: chamadas.append(caminho) or _dados_de_palavras())
    primeira = captura.palavras_da_imagem("x.jpg", "bib_01", 7)
    segunda = captura.palavras_da_imagem("x.jpg", "bib_01", 7)
    assert primeira == segunda and len(chamadas) == 1
    assert (tmp_path / "cache" / "bib_01" / "bib_01_00007.json").exists()


def test_anuncios_das_paginas_grava_no_banco(tmp_path, monkeypatch, capsys):
    from hdb.banco import BancoMemoria

    monkeypatch.setattr(config, "OCR_PALAVRAS_DIR", tmp_path / "cache")
    monkeypatch.setattr(captura.ocr, "ler_palavras", lambda caminho: _dados_de_palavras())
    pasta = tmp_path / "imgs" / "b"
    pasta.mkdir(parents=True)
    (pasta / "b_00005.jpg").write_bytes(b"x")
    (pasta / "b_00006.jpg").write_bytes(b"x")  # esta não está no banco
    banco = BancoMemoria()
    pagina = banco.garantir_pagina({"bib": "b", "pagina_fisica": "5", "termo": "t", "ocorrencia": 1})
    captura.anuncios_das_paginas(banco, [tmp_path / "imgs"], versao="v1")
    achados = banco.anuncios(pagina["id"], "v1")
    assert len(achados) == 1 and achados[0]["abertura"] == "VENDE-SE"
    saida = capsys.readouterr().out
    assert "b p.5: 1 colunas" in saida and "1 anúncios, 1 com abertura" in saida
    assert "b p.6: página desconhecida" in saida


def test_anuncios_sem_banco_nao_consulta_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OCR_PALAVRAS_DIR", tmp_path / "cache")
    monkeypatch.setattr(captura.ocr, "ler_palavras", lambda caminho: _dados_de_palavras())
    pasta = tmp_path / "imgs" / "b"
    pasta.mkdir(parents=True)
    (pasta / "b_00005.jpg").write_bytes(b"x")
    captura.anuncios_das_paginas(None, [tmp_path / "imgs"], limite=1)
