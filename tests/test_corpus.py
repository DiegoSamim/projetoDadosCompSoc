from hdb import config
from hdb.banco import BancoMemoria
from hdb.corpus import formatar_resumo, padronizar, processar, selecionar

JC_1840 = ("FUGIO hum molecote de 14 a 16 annos de idade, de nação Benguella, de nome Joaquim, levando vestido "
           "camiza de baeta amarela e calças de lila preta, bastante relinto; adverte-se que fugio na sabbado 4 do "
           "corrente; quem do mesmo der noticias, dirijase ao largo do Paço n, 5.")


def anuncio(**kw):
    return {"c_tipo": "fuga", "confianca": 80, "texto": " ".join(["palavra"] * 10), **kw}


def test_padronizar_anuncio_real_de_1840():
    palavras = padronizar(JC_1840).split()
    for esperada in ("fugiu", "molecote", "anos", "benguela", "joaquim", "camisa", "baeta", "calcas", "nacao"):
        assert esperada in palavras
    assert palavras.count("fugiu") == 2 and "sabado" in palavras
    for ausente in ("hum", "um", "de", "fugio", "annos", "camiza", "benguella", "largo", "paco", "14", "16", "4", "5", "n"):
        assert ausente not in palavras
    assert not any(c.isdigit() or c in ",;.-" for c in padronizar(JC_1840))


def test_padronizar_grafia_enderecos_e_tokens_curtos():
    assert padronizar("Huma preta, pharmacia; Rua do Rozario n. 107, tratase") == "preta farmacia tratase"
    assert padronizar("Vende-se o escravo de 20 annos na rua Direita n.º 5, com 2 filhos") == "vende escravo anos filhos"
    assert padronizar(None) == "" and padronizar("a o de 12") == ""


def test_padronizar_nao_altera_o_original():
    banco = BancoMemoria()
    banco.registrar_anuncios(1, "v2", [{"ordem": 1, "texto": JC_1840, "confianca": 80}])
    banco.registrar_campos("c2", [{"anuncio_id": 1, "tipo": "fuga"}])
    processar(banco, "c2", "corp1")
    assert banco.anuncios(1)[0]["texto"] == JC_1840


def test_selecionar():
    assert selecionar(anuncio())
    assert selecionar(anuncio(confianca=50, texto="um dois tres quatro cinco seis sete oito"))
    assert not selecionar(anuncio(c_tipo="outro")) and not selecionar(anuncio(c_tipo=None))
    assert not selecionar(anuncio(confianca=49.9)) and not selecionar(anuncio(confianca=None))
    assert not selecionar(anuncio(texto="um dois tres quatro cinco seis sete"))
    assert not selecionar(anuncio(texto=None))
    assert config.CORPUS_CONFIANCA_MIN == 50 and config.CORPUS_PALAVRAS_MIN == 8


def banco_do_corpus():
    banco = BancoMemoria()
    for pagina, ano in ((1, 1840), (2, 1860), (3, 1880)):
        banco.garantir_pagina({"bib": "b", "pagina_fisica": pagina, "ano": ano})
    banco.registrar_anuncios(1, "v2", [{"ordem": 1, "texto": JC_1840, "confianca": 90},
                                       {"ordem": 2, "texto": "FUGIO hum preto", "confianca": 90},
                                       {"ordem": 3, "texto": JC_1840, "confianca": 10}])
    banco.registrar_anuncios(2, "v2", [{"ordem": 1, "texto": JC_1840, "confianca": 90}])
    banco.registrar_anuncios(3, "v2", [{"ordem": 1, "texto": JC_1840, "confianca": 90}])
    for id_, tipo in ((1, "fuga"), (2, "fuga"), (3, "fuga"), (4, "outro"), (5, "venda")):
        banco.registrar_campos("c2", [{"anuncio_id": id_, "tipo": tipo}])
    banco.registrar_campos("c1", [{"anuncio_id": 5, "tipo": "outro"}])
    return banco


def test_processar_grava_so_os_selecionados_e_resume():
    banco = banco_do_corpus()
    r = processar(banco, "c2", "corp1", lote=1)
    assert sorted(i for i, _ in banco.corpus) == [1, 5]
    linha = banco.corpus[(1, "corp1")]
    assert linha["texto_padrao"] == padronizar(JC_1840) and linha["n_palavras"] == len(linha["texto_padrao"].split())
    assert r["total"] == 5 and r["selecionados"] == 2
    assert r["descartados"] == {"curto": 1, "confianca": 1, "tipo": 1}
    assert r["por_tipo"]["fuga"] == [1, 2] and r["por_tipo"]["venda"] == [1, 0]
    assert r["por_periodo"]["1831–1850 (Feijó → Eusébio)"] == [1, 2]
    assert r["por_periodo"]["1871–1888 (Ventre Livre → Áurea)"] == [1, 0]
    texto = formatar_resumo(r)
    assert "2 no corpus, 3 descartados" in texto and "1850–1871" in texto and "fuga: 1 selecionados" in texto


def test_processar_e_idempotente_e_respeita_versao_dos_campos():
    banco = banco_do_corpus()
    processar(banco, "c2", "corp1")
    antes = dict(banco.corpus)
    processar(banco, "c2", "corp1")
    assert banco.corpus.keys() == antes.keys()
    assert processar(banco, "c1", "corp2")["total"] == 1 and list(banco.corpus)[-1][1] != "corp2"
    assert processar(BancoMemoria(), "c2")["total"] == 0
