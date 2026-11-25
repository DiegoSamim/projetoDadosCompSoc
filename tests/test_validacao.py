import importlib.util
import json
import math
from pathlib import Path

import pytest

from hdb import config, validacao
from hdb.banco import BancoMemoria

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts" / "sortear_campos.py"
P1, P2, P3, P4 = validacao.PERIODOS

COM_TUDO = ("FUGIO o escravo Joao, de nação Congo, com 30 annos de idade, com uma cicatriz na barriga; "
            "quem o pegar será gratificado.")
SEM_NADA = "FUGIO o escravo Joao, estatura regular; quem o pegar leve-o a rua Direita."
MULHER = "ALUGA-SE uma preta, boa lavadeira, rua Direita n. 5."


def fuga(i, texto, periodo=P2, **rot):
    base = {"recompensa": False, "nacoes": [], "idade": None, "marcas": False, "sexo": "nao_diz"}
    return {"id": i, "periodo": periodo, "tipo": "fuga", "texto": texto, "rotulos": {**base, **rot}}


@pytest.fixture(scope="module")
def sortear():
    spec = importlib.util.spec_from_file_location("sortear_campos", ARQUIVO)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_extrair_para_comparar_formato():
    e = validacao.extrair_para_comparar(COM_TUDO)
    assert e["recompensa"] is True and e["marcas"] is True
    assert e["nacoes"] == ["congo"] and e["idade"][0] == 30 and e["sexo"] in ("m", "f", "ambos", "nao_diz")
    v = validacao.extrair_para_comparar(SEM_NADA)
    assert v["recompensa"] is False and v["nacoes"] == [] and v["idade"] is None and v["marcas"] is False


def test_contadores_por_campo():
    gold = [fuga(1, COM_TUDO, recompensa=True, nacoes=["Congo"], idade=30, marcas=True),   # tudo certo
            fuga(2, SEM_NADA, recompensa=True, nacoes=["mina"], idade=25, marcas=True),    # código perde tudo (FN)
            fuga(3, COM_TUDO, recompensa=False, nacoes=[], idade=None, marcas=False),      # código inventa (FP)
            fuga(4, SEM_NADA)]                                                             # tudo certo (VN)
    r = validacao.comparar(gold)
    for campo in ("recompensa", "nacao", "marcas", "idade"):
        c = r[campo][validacao.TOTAL]
        assert (c["vp"], c["fp"], c["fn"], c["vn"]) == (1, 1, 1, 1), campo
        assert {e["id"] for e in c["erros"]} == {2, 3}
    m = validacao.metricas(r["recompensa"][validacao.TOTAL])
    assert m["precisao"][0] == 0.5 and m["cobertura"][0] == 0.5 and m["f1"][0] == 0.5
    assert m["precisao"][1] < 0.5 < m["precisao"][2]
    assert r["recompensa"][P2]["vp"] == 1


def test_item_sem_rotulos_e_ignorado():
    gold = [{"id": 1, "periodo": P2, "tipo": "fuga", "texto": COM_TUDO}, fuga(2, SEM_NADA)]
    r = validacao.comparar(gold)
    assert r["recompensa"][validacao.TOTAL]["vn"] == 1
    assert sum(r["recompensa"][validacao.TOTAL][k] for k in ("vp", "fp", "fn", "vn")) == 1


def test_metricas_nan_sem_denominador():
    m = validacao.metricas({"vp": 0, "fp": 0, "fn": 0, "vn": 3, "erros": []})
    assert math.isnan(m["precisao"][0]) and math.isnan(m["cobertura"][0]) and math.isnan(m["f1"][0])


def test_idade_com_tolerancia_de_um_ano():
    def acerto(rotulo):
        r = validacao.comparar([fuga(1, COM_TUDO, idade=rotulo)])["idade_acerto"][validacao.TOTAL]
        return r["vp"], r["fp"]
    assert acerto(30) == (1, 0) and acerto(29) == (1, 0) and acerto(31) == (1, 0)
    assert acerto(32) == (0, 1) and acerto(27) == (0, 1)
    assert acerto([28, 40]) == (1, 0) and acerto([31, 40]) == (1, 0) and acerto([32, 40]) == (0, 1)


def test_sexo_acerto_e_marcacao_errada():
    gold = [fuga(1, COM_TUDO, sexo="m"), fuga(2, COM_TUDO, sexo="f"),          # código diz m: um certo, um errado
            fuga(3, COM_TUDO, sexo="ambos"), fuga(4, COM_TUDO, sexo="nao_diz"),  # marcou m onde não devia
            fuga(5, "FUGIO Joao, estatura regular, rua Direita.", sexo="f"),                                       # código não achou: perde cobertura
            {"id": 6, "periodo": P2, "tipo": "aluguel", "texto": MULHER, "rotulos": {"sexo": "f"}}]
    e = validacao.extrair_para_comparar(COM_TUDO)["sexo"]
    assert e == "m"
    r = validacao.comparar(gold)
    ac = r["sexo_acerto"][validacao.TOTAL]
    assert ac["vp"] == 1 + (validacao.extrair_para_comparar(MULHER)["sexo"] == "f") and ac["fp"] >= 1
    s = r["sexo"][validacao.TOTAL]
    assert s["fp"] == 2 and s["fn"] >= 1          # 'ambos' e 'nao_diz' marcados m
    assert {3, 4} <= {x["id"] for x in s["erros"]}


def contagem(vp, fn):
    return {"vp": vp, "fn": fn, "fp": 0, "vn": 0, "erros": []}


def test_fisher_sinaliza_queda_construida():
    ca, cu, queda, p, sinal = validacao.queda_de_cobertura({P1: contagem(18, 2), P4: contagem(8, 12)})
    assert ca == 0.9 and cu == 0.4 and queda == pytest.approx(50) and p < 0.05 and sinal is True


def test_fisher_nao_sinaliza_queda_estavel():
    ca, cu, queda, p, sinal = validacao.queda_de_cobertura({P1: contagem(18, 2), P4: contagem(17, 3)})
    assert queda == pytest.approx(5) and p > 0.05 and sinal is False


def test_sem_n_quando_faltam_positivos():
    assert validacao.queda_de_cobertura({P1: contagem(18, 2), P4: contagem(5, 5)}) == "sem n"
    assert validacao.queda_de_cobertura({P1: contagem(18, 2)}) == "sem n"
    # períodos do meio sem n são pulados: compara o primeiro e o último com n suficiente
    r = validacao.queda_de_cobertura({P1: contagem(18, 2), P2: contagem(3, 1), P3: contagem(19, 1), P4: contagem(2, 2)})
    assert r[0] == 0.9 and r[1] == 0.95


# --- sorteio ---

def banco_simulado():
    b = BancoMemoria()
    anos = {P1: 1820, P2: 1840, P3: 1860, P4: 1880}
    textos, i = {}, 0
    for per, ano in anos.items():
        for tipo, n in (("fuga", 40), ("aluguel", 25)):
            for _ in range(n):
                i += 1
                b.corpus[(i, config.VERSAO_CORPUS)] = {"texto_padrao": f"texto {i}"}
                b.campos[(i, config.VERSAO_CAMPOS)] = {"tipo": tipo}
                b.paginas[i] = {"ano": ano}
                b.lista_anuncios[(i, config.VERSOES_ANUNCIOS[0])] = [{"id": i}]
                textos[i] = f"  Original   {i}\n com   espaços " + "x" * 800
    return b, textos


def test_sorteio_reproduzivel_e_por_periodo(sortear):
    b, textos = banco_simulado()
    a = sortear.sortear(b, textos, aviso=lambda *_: None)
    c = sortear.sortear(b, textos, aviso=lambda *_: None)
    assert [i["id"] for i in a] == [i["id"] for i in c]
    assert len(a) == 120 and len({i["id"] for i in a}) == 120
    for per in validacao.PERIODOS:
        assert sum(i["tipo"] == "fuga" and i["periodo"] == per for i in a) == 20
        assert sum(i["tipo"] == "aluguel" and i["periodo"] == per for i in a) == 10
    assert all(set(i) == {"id", "periodo", "tipo", "texto"} and len(i["texto"]) <= 700 for i in a)
    assert a[0]["texto"].startswith("Original 1") or "  " not in a[0]["texto"]
    outra = sortear.sortear(b, textos, semente=1, aviso=lambda *_: None)
    assert [i["id"] for i in outra] != [i["id"] for i in a]


def test_sorteio_exclui_conferencia_e_avisa(sortear):
    b, textos = banco_simulado()
    a = sortear.sortear(b, textos, aviso=lambda *_: None)
    excluir = {i["id"] for i in a[:30]}
    avisos = []
    d = sortear.sortear(b, textos, excluir=excluir, aviso=avisos.append)
    assert not excluir & {i["id"] for i in d} and len(d) == 120
    # período com menos que o pedido: pega todos e avisa
    d = sortear.sortear(b, textos, excluir={i for i in range(1, 100)}, aviso=avisos.append)
    assert avisos and len(d) < 120
    assert len(sortear.ids_excluidos()) > 100  # lê conferencia.json e conferencia_extra.json


def test_nao_sobrescreve_arquivo_com_rotulos(sortear, tmp_path, capsys):
    b, textos = banco_simulado()
    arq = tmp_path / "gold.json"
    arq.write_text(json.dumps([{"id": 1, "rotulos": {"sexo": "f"}}]), encoding="utf-8")
    assert sortear.main([], banco=b, saida=arq, textos=textos) == 1
    assert json.loads(arq.read_text())[0]["rotulos"] == {"sexo": "f"}
    assert "rótulos" in capsys.readouterr().out
    assert sortear.main(["--forcar"], banco=b, saida=arq, textos=textos) == 0
    assert len(json.loads(arq.read_text())) == 120
    assert sortear.main([], banco=b, saida=arq, textos=textos) == 0  # sem rótulos: pode regravar
