import importlib.util
import json
from pathlib import Path

import pytest

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts" / "avaliar_limpeza.py"
LONGO = " ".join(["palavra"] * 40)
FUGA = "FUGIO do abaixo assignado o escravo Joao, de nação Congo, com 30 annos de idade; quem o pegar leve-o a rua Direita. " + LONGO
RUIDO = "Vapor inglez entrou do porto de Liverpool com carga de carvão e ferragens. " + LONGO


@pytest.fixture(scope="module")
def avaliar():
    spec = importlib.util.spec_from_file_location("avaliar_limpeza", ARQUIVO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def item(i, texto, e_anuncio, tipo_c4, tipo_certo, periodo="1850–1871"):
    return {"id": i, "periodo": periodo, "texto": texto, "tipo_c4": tipo_c4,
            "e_anuncio": e_anuncio, "tipo_certo": tipo_certo}


def gravar(tmp_path, itens):
    arq = tmp_path / "conf.json"
    arq.write_text(json.dumps(itens), encoding="utf-8")
    return arq


def test_arquivo_ausente_da_mensagem_clara(avaliar, tmp_path):
    with pytest.raises(SystemExit) as e:
        avaliar.carregar(tmp_path / "nao_existe.json")
    assert "conferência não encontrada" in str(e.value)


def test_conta_ruido_perdidos_e_tipo_certo(avaliar):
    itens = [item(1, FUGA, True, "fuga", "fuga"),
             item(2, RUIDO, False, "venda", None),     # c4 deixava entrar; o código atual não
             item(3, "texto curto", True, "outro", "venda")]  # anúncio real que fica de fora
    r = avaliar.avaliar(itens)["TOTAL"]
    assert r["n"] == 3 and r["verdadeiros"] == 2
    assert r["ruido_c4"] == 1 and r["ruido"] == 0
    assert r["perdidos"] == 1 and r["perdidos_c4"] == 0  # no corpus antigo todos os itens entravam
    assert r["tipo_certo"] == 1 and r["tipo_certo_c4"] == 1
    assert r["entram"] == 1 and r["entram_c4"] == 3


def test_item_incerto_fica_fora_da_conta(avaliar):
    itens = [item(1, FUGA, True, "fuga", "fuga"), item(2, "Fugio no dia 25 de dezembro rua de Ma R", None, "fuga", None)]
    r = avaliar.avaliar(itens)["TOTAL"]
    assert r["n"] == 1 and r["verdadeiros"] == 1


def test_metas_e_codigo_de_saida(avaliar, tmp_path, capsys):
    bom = [item(i, FUGA, True, "fuga", "fuga") for i in range(1, 40)] + [item(100, RUIDO, False, "venda", None)]
    assert avaliar.main([str(gravar(tmp_path, bom))]) == 0
    saida = capsys.readouterr().out
    assert "Ruído no corpus" in saida and "1850–1871" in saida and "TOTAL" in saida
    ruim = [item(1, FUGA, True, "fuga", "fuga"), item(2, "curto", True, "outro", "fuga")]  # 50% perdidos
    assert avaliar.main([str(gravar(tmp_path, ruim))]) == 1
    assert "FALHOU" in capsys.readouterr().out
