import random

import numpy as np

from hdb import config
from hdb.banco import BancoMemoria
from hdb.topicos import (ajustar, anuncios_tipicos, formatar_resumo, misturas, palavras_dos_topicos, processar)

TEMAS = {
    "fuga": "fugiu escravo fugido fujao matto capitao rastro recompensa gratifica levou fugida",
    "ama": "ama leite amamentar criar crianca parida peito saudavel mulher filho leiteira",
    "domestico": "cozinheira engomar lavar cozinha domestico costura casa servico forno tacho copeira",
}


def corpus(por_tema=10):
    """Mini-corpus sintético: 3 temas bem separados, 10 textos cada; devolve (textos, tema de cada texto)."""
    rng = random.Random(1)
    textos, temas = [], []
    for tema, palavras in TEMAS.items():
        lista = palavras.split()
        for _ in range(por_tema):
            textos.append(" ".join(rng.choices(lista, k=14)))
            temas.append(tema)
    return textos, temas


def banco_com_corpus(textos, versao="corp1"):
    banco = BancoMemoria()
    banco.registrar_corpus(versao, [{"anuncio_id": i + 1, "texto_padrao": t, "n_palavras": 14} for i, t in enumerate(textos)])
    return banco


def test_tres_temas_se_separam():
    textos, temas = corpus()
    modelo, vet, matriz = ajustar(textos, 3, 0)
    mist = misturas(modelo, matriz)
    dominante = np.argmax(mist, axis=1)
    for tema in TEMAS:
        do_tema = {int(d) for d, t in zip(dominante, temas) if t == tema}
        assert len(do_tema) == 1  # todos os textos do tema caem no mesmo tópico
    assert len({int(dominante[i]) for i in (0, 10, 20)}) == 3  # e os três temas em tópicos diferentes
    palavras = palavras_dos_topicos(modelo, vet.get_feature_names_out(), n=5)
    for t, lista in enumerate(palavras):
        tema = temas[list(dominante).index(t)]
        assert all(p in TEMAS[tema].split() for p, _ in lista)
        assert all(0 < w < 1 for _, w in lista) and [w for _, w in lista] == sorted((w for _, w in lista), reverse=True)


def test_misturas_somam_um_e_tipicos():
    textos, temas = corpus()
    modelo, vet, matriz = ajustar(textos, 3, 0)
    mist = misturas(modelo, matriz)
    assert mist.shape == (30, 3) and np.allclose(mist.sum(axis=1), 1)
    ids = list(range(100, 130))
    tipicos = anuncios_tipicos(mist, ids, n=4)
    assert len(tipicos) == 3 and all(len(t) == 4 for t in tipicos)
    for t, lista in enumerate(tipicos):
        assert all(mist[i - 100, t] == mist[:, t].max() or mist[i - 100, t] > 0.5 for i in lista)
        assert len({temas[i - 100] for i in lista}) == 1


def test_semente_fixa_reproduz():
    textos, _ = corpus()
    a = misturas(*[ajustar(textos, 3, 0)[i] for i in (0, 2)])
    b = misturas(*[ajustar(textos, 3, 0)[i] for i in (0, 2)])
    assert np.allclose(a, b)


def test_processar_grava_e_resume():
    textos, _ = corpus()
    banco = banco_com_corpus(textos)
    r = processar(banco, "corp1", 3, 0, "t1")
    m = banco.topico_modelos["t1"]
    assert (m["n_topicos"], m["n_docs"], m["versao_corpus"], m["semente"]) == (3, 30, "corp1", 0)
    assert m["n_vocab"] == 33 and m["perplexidade"] > 0
    assert len(banco.anuncio_topicos) == 90
    for i in range(1, 31):
        assert abs(sum(banco.anuncio_topicos[(i, "t1", t)] for t in range(3)) - 1) < 1e-5
    assert len(banco.topico_palavras) == 3 * config.TOPICOS_PALAVRAS
    assert sorted(t["n"] for t in r["topicos"]) == [10, 10, 10]
    texto = formatar_resumo(r)
    assert "Tópico 0" in texto and "perplexidade" in texto and "sem ano" in texto


def test_resumo_usa_periodo_e_tipo():
    textos, _ = corpus()
    banco = banco_com_corpus(textos)
    banco.registrar_anuncios(1, "v2", [{"ordem": i, "texto": "x"} for i in range(30)])
    banco.registrar_campos("c3", [{"anuncio_id": i, "tipo": "fuga" if i <= 10 else "aluguel"} for i in range(1, 31)])
    r = processar(banco, "corp1", 3, 0, "t1")
    tipos = sum((t["por_tipo"] for t in r["topicos"]), type(r["topicos"][0]["por_tipo"])())
    assert tipos == {"fuga": 10, "aluguel": 20}


def test_regravar_substitui_tudo():
    textos, _ = corpus()
    banco = banco_com_corpus(textos)
    processar(banco, "corp1", 3, 0, "t1")
    processar(banco, "corp1", 2, 0, "t1")
    processar(banco, "corp1", 2, 0, "t2")
    assert banco.topico_modelos["t1"]["n_topicos"] == 2
    assert {t for (_, v, t) in banco.anuncio_topicos if v == "t1"} == {0, 1}
    assert {t for (v, t, _) in banco.topico_palavras if v == "t1"} == {0, 1}
    assert len([k for k in banco.anuncio_topicos if k[1] == "t1"]) == 60 and len(banco.anuncio_topicos) == 120


def test_corpus_vazio_avisa():
    import pytest
    with pytest.raises(ValueError):
        processar(BancoMemoria(), "corp1", 3, 0, "t1")
