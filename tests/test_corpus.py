from hdb import config
from hdb.banco import BancoMemoria
from hdb.corpus import (MOTIVOS, cortar_colado, descobrir_ocr, formatar_resumo, motivo_descarte, padronizar, processar,
                        selecionar)

JC_1840 = ("FUGIO hum molecote de 14 a 16 annos de idade, de nação Benguella, de nome Joaquim, levando vestido "
           "camiza de baeta amarela e calças de lila preta, bastante relinto; adverte-se que fugio na sabbado 4 do "
           "corrente; quem do mesmo der noticias, dirijase ao largo do Paço n, 5.")


def anuncio(**kw):
    return {"c_tipo": "fuga", "confianca": 80, "texto": "escravo " + " ".join(["palavra"] * 9), **kw}


def test_padronizar_anuncio_real_de_1840():
    palavras = padronizar(JC_1840).split()
    for esperada in ("fugiu", "molecote", "anos", "benguela", "camisa", "baeta", "calcas", "nacao"):
        assert esperada in palavras
    assert palavras.count("fugiu") == 2 and "sabado" in palavras
    for ausente in ("hum", "um", "de", "joaquim", "fugio", "annos", "camiza", "benguella", "largo", "paco", "14", "16", "4", "5", "n"):
        assert ausente not in palavras
    assert not any(c.isdigit() or c in ",;.-" for c in padronizar(JC_1840))


def test_padronizar_grafia_enderecos_e_tokens_curtos():
    assert padronizar("Huma preta, pharmacia; Rua do Rozario n. 107, tratase") == "preta farmacia tratase"
    assert padronizar("Vende-se o escravo de 20 annos na rua Direita n.º 5, com 2 filhos") == "vende escravo anos filhos"
    assert padronizar(None) == "" and padronizar("a o de 12") == ""


def test_ocr_unifica_aluga_precisa_e_quiser():
    assert padronizar("Luga-se uma preta. Aluga-se outra; recisa-se de ama; ecisa cozinheiro; quizer ende") == \
        "aluga preta aluga outra precisa ama precisa cozinheiro quiser vende"
    assert padronizar("ras rus ros nde bum huma") == ""


def test_nomes_e_loteria_saem():
    texto = "Vende-se preto Jose Antonio Pedro, comprou por conta; bilhete e bilhetes da loteria, Joaquim Maria"
    assert padronizar(texto) == "vende preto"


def test_padronizar_nao_altera_o_original():
    banco = BancoMemoria()
    banco.registrar_anuncios(1, "v2", [{"ordem": 1, "texto": JC_1840, "confianca": 80}])
    banco.registrar_campos("c2", [{"anuncio_id": 1, "tipo": "fuga"}])
    processar(banco, "c2", "corp1")
    assert banco.anuncios(1)[0]["texto"] == JC_1840


def test_selecionar():
    assert selecionar(anuncio())
    assert selecionar(anuncio(confianca=50, texto="escravo dois tres quatro cinco seis sete oito"))
    assert not selecionar(anuncio(c_tipo="outro")) and not selecionar(anuncio(c_tipo=None))
    assert not selecionar(anuncio(c_tipo="aluguel_incerto"))
    assert motivo_descarte(anuncio(c_tipo="aluguel_incerto")) == "incerto" and "incerto" in MOTIVOS
    assert selecionar(anuncio(c_tipo="aluguel"))
    assert not selecionar(anuncio(confianca=49.9)) and not selecionar(anuncio(confianca=None))
    assert not selecionar(anuncio(texto="escravo dois tres quatro cinco seis sete"))
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


CAUTELA = ("Desappareceu uma cautela do monte do soccorro, pertencente a Joaquim da Silva, quem a achar "
           "queira entregar na rua da Alfandega, que receberá alviçaras.")
COLADO = ("VENDE-SE uma preta de 20 annos, boa cozinheira; na rua do Ouvidor n. 118 — ALUGA-SE uma casa terrea "
          "na rua do Hospicio n. 20")


def test_fuga_sem_pessoa_fica_fora_do_corpus():
    assert "sem_pessoa" in MOTIVOS
    assert motivo_descarte(anuncio(texto=CAUTELA)) == "sem_pessoa" and not selecionar(anuncio(texto=CAUTELA))
    assert selecionar(anuncio(texto="FUGIO hum escravo de nome Francisco, Angola, levou camisa de algodao"))
    assert selecionar(anuncio(c_tipo="venda", texto=CAUTELA))  # só vale para a fuga
    assert motivo_descarte(anuncio(c_tipo="outro", texto=CAUTELA)) == "tipo"  # ordem: tipo antes de sem_pessoa


def test_cortar_colado_corta_no_segundo_anuncio():
    cortado = cortar_colado(COLADO)
    assert cortado.endswith("n. 118 — ") and "ALUGA" not in cortado and cortado.startswith("VENDE-SE")
    assert padronizar(COLADO) == "vende preta anos boa cozinheira"
    assert "terrea" in padronizar("ALUGA-SE uma casa terrea") and "terrea" not in padronizar(COLADO)
    assert cortar_colado("VENDE-SE uma casa terrea na rua Direita; ALUGA-SE uma preta de 20 annos, boa cozinheira") == \
        "ALUGA-SE uma preta de 20 annos, boa cozinheira"  # nenhum trecho de pessoa no 1º: fica o da preta
    assert cortar_colado("ALUGA-SE uma preta de 20 annos, cozinheira; VENDE-SE um preto de 30 annos, sapateiro") == \
        "ALUGA-SE uma preta de 20 annos, cozinheira; "  # dois trechos com pessoa: só o 1º
    ambos = "vende-se ou aluga-se uma preta de boa conducta, cozinheira e lavadeira"
    assert cortar_colado(ambos) == ambos and cortar_colado(None) == ""


def test_despolpador_fica_o_trecho_da_preta():
    texto = ("VENDE-SE um despolpador de café em bom estado, na rua do Ouvidor n. 12 — VENDE SE ou aluga se uma preta "
             "ama de leite, boa lavadeira, sem vicios")
    assert cortar_colado(texto).startswith("VENDE SE ou aluga se uma preta")
    assert "despolpador" not in padronizar(texto) and "preta" in padronizar(texto)
    assert selecionar(anuncio(c_tipo="fuga", texto=texto))  # a pessoa e avaliada no texto cortado


def textos_de_ocr():
    return (["vendedor preta"] * 30 + ["endedor preta"] * 3  # endedor -> vendedor (razao 10)
            + ["alugam casa"] * 40 + ["lugam casa"] * 3
            + ["compra"] * 200 + ["compro"] * 25)  # compro e frequente demais


def test_descobrir_ocr_aplica_recusa_ambiguo_e_frequente():
    r = descobrir_ocr(textos_de_ocr())
    assert r["aplicadas"] == {"endedor": "vendedor", "lugam": "alugam"}
    motivos = {w: (v, m) for w, v, _, _, m in r["recusadas"]}
    assert motivos["compro"] == ("compra", "frequente")
    assert descobrir_ocr(["vendedor preta"] * 30 + ["ende preta"] * 4)["aplicadas"] == {}  # razao 7,5 < 8
    assert descobrir_ocr(["vendedor preta"] * 32 + ["endedor preta"] * 4)["aplicadas"] == {"endedor": "vendedor"}


def test_descobrir_ocr_ambiguo_so_lista():
    textos = ["fugiu preta"] * 40 + ["fugia preta"] * 30 + ["fugiz preta"] * 2
    r = descobrir_ocr(textos)
    assert r["aplicadas"] == {} and r["recusadas"] == [("fugiz", "fugiu", 2, 40, "ambiguo")]
    assert descobrir_ocr(["vende"] * 50 + ["ver"] * 3)["aplicadas"] == {}  # menos de 4 letras
    assert descobrir_ocr(["hum um um um"] * 50 + ["hun"] * 2)["aplicadas"] == {}


def test_processar_aplica_ocr_descoberto_e_manual_ganha():
    banco = BancoMemoria()
    banco.garantir_pagina({"bib": "b", "pagina_fisica": 1, "ano": 1850})
    banco.registrar_anuncios(1, "v2", [{"ordem": i, "texto": "Vende-se uma preta engomadeira de bom genio e saude", "confianca": 90}
                                       for i in range(1, 41)]
                                      + [{"ordem": 41, "texto": "Vende-se uma preta ngomadeira de bom genio e saude", "confianca": 90}])
    banco.registrar_campos("c2", [{"anuncio_id": i, "tipo": "venda"} for i in range(1, 42)])
    r = processar(banco, "c2", "corp1")
    assert r["ocr_descoberto"]["aplicadas"] == {"ngomadeira": "engomadeira"}
    assert banco.corpus[(41, "corp1")]["texto_padrao"] == banco.corpus[(1, "corp1")]["texto_padrao"]
    assert "ngomadeira -> engomadeira" in formatar_resumo(r) and "1 trocas aplicadas" in formatar_resumo(r)
    assert padronizar("ende ngomadeira", {"ende": "xxxx", "ngomadeira": "engomadeira"}) == "vende engomadeira"  # manual (OCR) ganha


def test_incluir_incertos_so_com_a_flag():
    incerto = anuncio(c_tipo="aluguel_incerto")
    assert motivo_descarte(incerto) == "incerto" and not selecionar(incerto)
    assert motivo_descarte(incerto, incluir_incertos=True) is None and selecionar(incerto, True)
    assert motivo_descarte(anuncio(c_tipo="aluguel_incerto", confianca=10), True) == "confianca"
    banco = BancoMemoria()
    banco.garantir_pagina({"bib": "b", "pagina_fisica": 1, "ano": 1850})
    banco.registrar_anuncios(1, "v2", [{"ordem": 1, "texto": JC_1840, "confianca": 90}])
    banco.registrar_campos("c2", [{"anuncio_id": 1, "tipo": "aluguel_incerto"}])
    assert processar(banco, "c2", "corp3")["selecionados"] == 0 and not banco.corpus
    assert processar(banco, "c2", "corp3i", incluir_incertos=True)["selecionados"] == 1 and (1, "corp3i") in banco.corpus


def test_descobrir_ocr_so_aplica_perda_da_primeira_letra():
    """Sem dicionário, "uma letra de diferença" junta palavras legítimas (alho/alto): só vale o erro sistemático."""
    textos = ["alto preto"] * 40 + ["alho preto"] * 2 + ["engomadeira"] * 40 + ["ngomadeira"] * 2
    r = descobrir_ocr(textos)
    assert r["aplicadas"] == {"ngomadeira": "engomadeira"}
    assert ("alho", "alto", 2, 40, "nao_sistematico") in r["recusadas"]


def test_regravar_o_corpus_remove_quem_deixou_de_ser_selecionado():
    banco = BancoMemoria()
    banco.garantir_pagina({"bib": "b", "pagina_fisica": 1, "ano": 1850})
    banco.registrar_anuncios(1, "v2", [{"ordem": i, "texto": "Vende-se uma preta engomadeira de bom genio e saude", "confianca": 90}
                                       for i in range(1, 4)])
    banco.registrar_campos("c2", [{"anuncio_id": i, "tipo": "venda"} for i in range(1, 4)])
    processar(banco, "c2", "corp1")
    assert banco.ids_do_corpus("corp1") == [1, 2, 3]
    banco.registrar_campos("c2", [{"anuncio_id": 1, "tipo": "venda"}, {"anuncio_id": 2, "tipo": "outro"},
                                  {"anuncio_id": 3, "tipo": "venda"}])  # regra mais rígida: o 2 vira "outro"
    processar(banco, "c2", "corp1")
    assert banco.ids_do_corpus("corp1") == [1, 3]
