import pytest

from hdb.banco import BancoMemoria
from hdb.campos import (VERSAO_CAMPOS, classificar, extrair, extrair_anuncio, formatar_resumo, linha_do_banco,
                        processar, resumir)
from hdb.campos import _classificar

T1 = "VENDE-SE huma linda negrinha de 13 annos, que cose soflrivelmente, engomma, lava, e faz o mais"
T2 = "VENDE-SE hum molecote de 18 annos , peça , perito official de marceneiro de toda a obra, que dá"
T3 = "ALUGA-SE huma parda forra, boa ama de leite; na rua nova de 8, Bento n. 33."
T4 = "ALUGA-SE huma preta ama de leite do primeiro parto , que terá 19 annos de idade; na rua do Rozario n. 107."
T5 = ("PRECISA-SE alugar hum preto que saiba o serviço de huma casa; quem o tiver dirija-se à rua do Ouvidor "
      "n. 66, casa de leilão, ou à rua dos Ourives n. 38,")
T6 = "PRECISA-SE comprar alguns pretos de roça , velhos e de meia idade ; na rua da Misericordia n, 6"
T7 = ("34. AJohn Scurr fugirão no dia'17 de Julho do presente anno dous moleques Cabindas hum de 10 à 12 annos, "
      "ouiro de 16 a 18, ambos de calças brancas; quem delles souber, eos amarrar procure a seu Senhorna rua das "
      "Violas N.º 17, ou na praia do flamen: go nas cazas novas de Antonio da Cunha.")
T8 = ("35. Na noite do dia 11 do corrrente mez de julho dezapateceu huma negra inda boçal de Nação Cabinda saia de "
      "zuarte camiza de algodão prenhe, com hum barilfcom que hia a Carioca, rega se a toda pessoa que della tiver "
      "noticia queira partecipar a seu Sr. que he Joaquim Ferreira Guimarães, iua de S. Pedro N.º 56, do lado "
      "direito indo para sima que terá boas alviçaras,")
T9 = ("36 Fugio, ha 2 para 3 annos hnma preta Bengueila por nome Maria alta, rosto comprido, fula, olhos grande, "
      "calombo no peito; quem della souber ou der noticia dirija-se a rua da Cadeia N.º 203, a sahir ao largo da "
      "Carioca, que receberá de premio 32:000.")
T10 = ("37. A José Maria da Silva, fugio hum escravo há 8 mezes pouco mais ou menos, de nome Joaquim de Nação "
       "Cabunda, alto groço, official de Serrador, quem delle der noticia pode dirigir-se a Virgolino Mancel, com "
       "loja de louça na rua da Ajuda; onde receberá boas alviçaras;")
T11 = ("PRETO FUGIDO. Evadio-se o preto Crioulo por nome Luiz, que estay O em casa do seu senhor, por tentativas de "
       "crimes, Lise vendido para fór: lr eh ro «tem slgn: Je chagas antigas nas pern: parece ter 40 annos de idade")
T12 = "VENDE-SE uma linda escrava de nação Mina, sabendo lavar perfeitamente; na rua da Prainha n. 11."
T13 = "ALUGA-SE huma Sra. branca filha das Ilhas , que sabe muito bem coser, talhar e engommar"
NEGATIVOS = [
    "ALUGA-SE hum terceiro andar muito fresco , na rua do Ouvidor n. 126.",
    "COMPRA-SE hum piano usado , por preço modico; no largo da Carioca n. 2.",
    "VENDEM-SE , na rua do Ouvidor n. 87, loja de E. Mongie, os livros seguintes; Selecta latini",
    "Dia 11 de Abril. — Rio de S. João; 3 dias; E. S. José, M. Bernardino Francisco da Fônte, equipagem 5, carga madeira",
]

# (anúncio, tipo, procura, sexo, (idade_min, idade_max))
CLASSIFICACAO = [
    ({"texto": T1, "abertura": "VENDE-SE"}, "venda", False, "f", (13, 13)),
    ({"texto": T2, "abertura": "VENDE-SE"}, "venda", False, "m", (18, 18)),
    ({"texto": T3, "abertura": "ALUGA-SE"}, "ama_de_leite", False, "f", (None, None)),
    ({"texto": T4, "abertura": "ALUGA-SE"}, "ama_de_leite", False, "f", (19, 19)),
    ({"texto": T5, "abertura": "PRECISA-SE"}, "aluguel", True, "m", (None, None)),
    ({"texto": T6, "abertura": "PRECISA-SE"}, "compra", True, "m", (None, None)),
    ({"texto": T7, "abertura": "N."}, "fuga", False, "m", (10, 18)),
    ({"texto": T8, "abertura": "N."}, "fuga", False, "f", (None, None)),
    ({"texto": T9, "abertura": "N."}, "fuga", False, "f", (None, None)),
    ({"texto": T10, "abertura": "N."}, "fuga", False, "m", (None, None)),
    ({"texto": T11, "titulo": "PRETO FUGIDO.", "abertura": "EVADIO-SE"}, "fuga", False, "m", (40, 40)),
    ({"texto": T12}, "venda", False, "f", (None, None)),
]


@pytest.mark.parametrize("anuncio,tipo,procura,sexo,idade", CLASSIFICACAO)
def test_anuncios_reais(anuncio, tipo, procura, sexo, idade):
    r = extrair_anuncio(anuncio)
    assert (r["tipo"], r["procura"], r["sexo"], (r["idade_min"], r["idade_max"])) == (tipo, procura, sexo, idade)
    assert r["versao"] == VERSAO_CAMPOS


def test_campos_dos_anuncios_reais():
    assert extrair(T2)["oficios"] == ["marceneiro"]
    assert extrair(T3)["cores"] == ["pardo"] and extrair(T3)["condicao"] == "forro"
    assert "ama de leite" in extrair(T3)["oficios"]
    assert "rua do Rozario n. 107" in extrair(T4)["endereco"]
    assert extrair(T7)["nacoes"] == ["Cabinda"]
    r8 = extrair(T8)
    assert r8["nacoes"] == ["Cabinda"] and "boçal" in r8["cores"] and r8["recompensa"] is True
    r9 = extrair(T9)
    assert r9["nacoes"] == ["Benguela"] and r9["nomes"] == ["Maria"] and {"preto", "fula"} <= set(r9["cores"])
    assert r9["recompensa"] and r9["valor"] == "32:000" and r9["idade_min"] is None
    r10 = extrair(T10)
    assert r10["nomes"] == ["Joaquim"] and r10["nacoes"] == ["Cabundá"] and r10["oficios"] == ["serrador"]
    assert r10["condicao"] == "escravizado" and r10["idade_max"] is None
    r11 = extrair(T11)
    assert r11["nomes"] == ["Luiz"] and r11["cores"] == ["preto", "crioulo"]
    r12 = extrair(T12)
    assert r12["nacoes"] == ["Mina"] and r12["condicao"] == "escravizado"
    assert extrair(T5)["endereco"] == "rua do Ouvidor n. 66"
    assert extrair(T6)["endereco"] == "rua da Misericordia n, 6"


def test_condicao_livre_e_sra_branca_nao_e_aluguel_de_escravizada():
    assert extrair(T13)["condicao"] == "livre"
    assert classificar({"texto": T13, "abertura": "ALUGA-SE"}) == ("outro", False)  # c3: sem palavra de pessoa


@pytest.mark.parametrize("texto", NEGATIVOS)
def test_negativos_sao_outro(texto):
    assert classificar({"texto": texto, "abertura": None}) == ("outro", False)
    assert classificar({"texto": texto, "abertura": "VENDEM-SE"})[0] == "outro"


def test_precisa_se_pessoa_sem_verbo_e_aluguel_com_procura():
    assert classificar({"texto": "PRECISA-SE de huma preta para cozinhar", "abertura": "PRECISA-SE"}) == ("aluguel", True)


def test_compra_se_pessoa_e_procura():
    assert classificar({"texto": "COMPRA-SE huma escrava moça, que saiba cozinhar", "abertura": "COMPRA-SE"}) == ("compra", True)
    assert classificar({"texto": "COMPRAM-SE pretos novos", "abertura": "COMPRAM-SE"}) == ("compra", True)
    assert classificar({"texto": "VENDE-SE huma escrava", "abertura": "VENDE-SE"}) == ("venda", False)


def test_precisa_se_ama_de_leite_mantem_procura():
    assert classificar({"texto": "PRECISA-SE huma ama de leite", "abertura": "PRECISA-SE"}) == ("ama_de_leite", True)


def test_vende_se_com_fugio_no_texto_nao_vira_fuga():
    assert classificar({"texto": "VENDE-SE huma preta que nunca fugio", "abertura": "VENDE-SE"})[0] == "venda"


def test_secao_de_fuga_pelo_titulo():
    anuncio = {"texto": "huma preta de nome Rosa", "titulo": "E S C R A V O S  F U G I D O S ."}
    assert classificar(anuncio)[0] == "fuga"


def test_aviso_numerado_sem_palavra_de_fuga_nao_e_fuga():
    anuncio = {"texto": "12. Vende-se huma preta de 20 annos", "abertura": "N."}
    assert classificar(anuncio) == ("venda", False)


def test_sem_abertura_usa_o_verbo_do_texto():
    assert classificar({"texto": "huma preta; vende-se na rua do Ouvidor"})[0] == "venda"


@pytest.mark.parametrize("texto,faixa", [
    ("preta de 13 annos", (13, 13)), ("moleque de 13 a 14 annos", (13, 14)),
    ("pardo de 16 para 18 annos", (16, 18)), ("idade 20 e tantos annos", (20, 29)),
    ("que terá 19 annos", (19, 19)), ("40 annos de idade", (40, 40)), ("parece ter 40 annos", (40, 40)),
    ("de 13 ann0s", (13, 13)), ("de 13 anos", (13, 13)),
    ("fugio ha 2 para 3 annos", (None, None)), ("fugio há 8 mezes", (None, None)),
    ("fugio à 4 annos", (None, None)), ("de 150 annos", (None, None)), ("", (None, None)),
])
def test_idade(texto, faixa):
    r = extrair(texto)
    assert (r["idade_min"], r["idade_max"]) == faixa


@pytest.mark.parametrize("texto,nacoes", [
    ("preta Bengueila", ["Benguela"]), ("preta Bengnela", ["Benguela"]), ("dous Cabindas", ["Cabinda"]),
    ("de Nação Cabunda", ["Cabundá"]), ("de nação Moçambique", ["Moçambique"]), ("Nagô e Congo", ["Nagô", "Congo"]),
    ("Joaquim Rebelo", []), ("Angela", []), ("a mina de ouro", []), ("Cabinda e Cabindas", ["Cabinda"]),
])
def test_nacoes(texto, nacoes):
    assert extrair(texto)["nacoes"] == nacoes


@pytest.mark.parametrize("texto,nomes", [
    ("por nome Maria alta", ["Maria"]), ("de nome Joaquim de Nação Cabunda", ["Joaquim"]),
    ("chamado Pedro Antonio, fugio", ["Pedro Antonio"]), ("chamada Rosa", ["Rosa"]),
    ("nome Nação Mina", []), ("de nome ignorado", []),
])
def test_nomes(texto, nomes):
    assert extrair(texto)["nomes"] == nomes


@pytest.mark.parametrize("texto,valor", [
    ("premio 32:000.", "32:000"), ("gratifica 20$", "20$"), ("gratifica 20s", "20s"),
    ("2:000$000 por ella", "2:000$000"), ("100:000", "100:000"), ("na rua do Ouvidor n. 17", None),
])
def test_valor(texto, valor):
    assert extrair(texto)["valor"] == valor


@pytest.mark.parametrize("texto,endereco", [
    ("na rua do Ouvidor n. 12, ou", "rua do Ouvidor n. 12"), ("largo da Carioca N.º 17", "largo da Carioca N.º 17"),
    ("rua de S. Pedro n. 5", "rua de S. Pedro n. 5"), ("beco da Fortuna", None),
    ("praia do Flamengo n. 3 e rua A n. 4", "praia do Flamengo n. 3"),
])
def test_endereco(texto, endereco):
    assert extrair(texto)["endereco"] == endereco


def test_sexo():
    assert extrair("VENDE-SE hum preto e huma preta")["sexo"] == "ambos"
    assert extrair("hum preto")["sexo"] == "m"
    assert extrair("duas pretas")["sexo"] == "f"
    assert extrair("hum piano")["sexo"] is None


def test_recompensa_e_cores():
    assert extrair("quem a trouxer será gratificado")["recompensa"] is True
    assert extrair("gratifica-se bem")["recompensa"] is True
    assert extrair("hum pardo ladino")["cores"] == ["pardo", "ladino"]


def test_evidencias():
    r = extrair("hum preto de 20 annos, por nome Luiz")
    assert r["evidencias"]["nomes"] == "Luiz" and "20 annos" in r["evidencias"]["idade"]


@pytest.mark.parametrize("texto", [None, "", "   ", "\n"])
def test_extrair_nao_falha_com_vazio(texto):
    r = extrair(texto)
    assert r["sexo"] is None and r["nacoes"] == [] and r["recompensa"] is False and r["evidencias"] == {}
    assert extrair_anuncio({"texto": texto})["tipo"] == "outro"
    assert classificar({"texto": texto}) == ("outro", False)


# --- orquestração ---


def banco_com_anuncios():
    banco = BancoMemoria()
    banco.registrar_anuncios(1, "v2", [
        {"ordem": i, "texto": a["texto"], "titulo": a.get("titulo"), "abertura": a.get("abertura")}
        for i, (a, *_) in enumerate(CLASSIFICACAO, 1)])
    banco.registrar_anuncios(2, "v2", [{"ordem": i, "texto": t, "titulo": None, "abertura": None}
                                       for i, t in enumerate(NEGATIVOS, 1)])
    banco.registrar_anuncios(3, "v1", [{"ordem": 1, "texto": T1, "titulo": None, "abertura": "VENDE-SE"}])
    return banco


def test_processar_grava_um_registro_por_anuncio_da_versao():
    banco = banco_com_anuncios()
    r = processar(banco, "v2", lote=5)
    assert r["total"] == len(CLASSIFICACAO) + len(NEGATIVOS) == len(banco.campos)
    assert all(versao == VERSAO_CAMPOS for _, versao in banco.campos)
    por_texto = {a["texto"]: a["id"] for a in banco.anuncios_para_campos("v2")}
    assert banco.campos[(por_texto[T9], VERSAO_CAMPOS)]["valor"] == "32:000"
    assert banco.campos[(por_texto[T9], VERSAO_CAMPOS)]["nacoes"] == ["Benguela"]


def test_processar_e_idempotente_e_respeita_versao_e_limite():
    banco = banco_com_anuncios()
    processar(banco, "v2", limite=3)
    assert len(banco.campos) == 3
    processar(banco, "v2")
    processar(banco, "v2")
    processar(banco, "v2", versao="c9")
    assert len(banco.campos) == 2 * (len(CLASSIFICACAO) + len(NEGATIVOS))


def test_linha_do_banco_so_tem_listas_e_dict():
    linha = linha_do_banco(7, extrair_anuncio({"texto": None}))
    assert linha["anuncio_id"] == 7 and "versao" not in linha
    assert linha["nacoes"] == [] and linha["evidencias"] == {} and linha["tipo"] == "outro"


def test_resumo():
    r = processar(banco_com_anuncios(), "v2")
    assert r["por_tipo"] == {"venda": 3, "ama_de_leite": 2, "aluguel": 1, "compra": 1, "fuga": 5, "outro": 4}
    assert r["por_sexo"]["m"] >= 5 and r["por_sexo"]["sem"] == 4
    assert r["com_idade"] == 5 and r["com_nome"] == 3 and r["com_recompensa"] == 3
    assert dict(r["nacoes"])["Cabinda"] == 2
    texto = formatar_resumo(r)
    assert "16 anúncios processados" in texto and "Cabinda (2)" in texto
    assert resumir([])["total"] == 0


# --- casos reais da conferência (c2): contexto de pessoa, sexo, falsos negativos, nação espúria ---

REAIS = [  # (texto, abertura, tipo, procura, sexo)
    ("VENDE-SE, na chacara n. 87 da estrada dé S. GRERTOTÃO » huma boa carruagem, por preço com— modo, — O RAPÉ "
     "arta-preta da nova fabrica do Rio de Janeiro, affiançado tanto p", "VENDE-SE", "outro", False, None),
    ("lovas do retrez para 1500; dites para homesa, da todas as côres com dr de seda preta renito fio porca",
     None, "outro", False, None),
    ("ANGRA — 4 d., Sum. Maria Candida, M tons., M. Manoel José de Mello; equip. 6: carga 500 saccas café , "
     "a José Bernardo Brandão ; passag. 1 escravo a en", None, "outro", False, "m"),
    ("VENDE-SE huma rapariga para todo o serviço de huma casa, sabendo bem engommar roupa de Sra, e de homem: "
     "quem a pretender dirija-se à rua S. Jorge n.2.", "VENDE-SE", "venda", False, "f"),
    ("VENDEM-SE,, na rua dos Ourives n. 17, daas lindas negrinhas, huma de 16 annos, que cose, engomima, cozinha "
     "e lava, e outra de 17 annos. — MANOEL Ferreira de Faria e Comp.", "VENDEM-SE", "venda", False, "f"),
    ("PRE (gar uma preta que saiba lavar é en Eommar ; na praia de Hotafogo n. 70.", None, "aluguel", True, "f"),
    ("PRECISA-SE tugar hum preto para todo o setviço", "PRECISA-SE", "aluguel", True, "m"),
    ("Yseravos. Recebem-se para serem vendidos , fa- S ,endo-se as vendas com muita-brevidade ; na rua SG vin "
     "Alfandega m. tár CONTINUA-SE à receber escravo", None, "venda", False, "m"),
    ("E - s DESA o dem ia Resta pretas; quemo achar levar áruado Fogom.31 tá gratificado com 29000.",
     None, "fuga", False, None),
    ("A PESSOA que offereceu pela preta 4204000, na rua e S. Pedro n. 267, póde ir busca-la",
     None, "venda", False, "f"),
    ("24. Fabio no dia t7 do corrente hum moleque de idade 16 a 18 annos, Naçio Ganguella, por nome Manoel, tem "
     "os olhos vesgos alguma cora, Dan ferida no braço Pd quazi junto", "N.", "fuga", False, "m"),
]


@pytest.mark.parametrize("texto,abertura,tipo,procura,sexo", REAIS)
def test_casos_reais_da_conferencia(texto, abertura, tipo, procura, sexo):
    r = extrair_anuncio({"texto": texto, "abertura": abertura})
    assert (r["tipo"], r["procura"], r["sexo"]) == (tipo, procura, sexo)


def test_nacao_do_aviso_24_e_so_ganguela():
    r = extrair(REAIS[-1][0])
    assert r["nacoes"] == ["Ganguela"] and r["nomes"] == ["Manoel"] and (r["idade_min"], r["idade_max"]) == (16, 18)


def test_cor_de_objeto_nao_e_cor_de_pessoa():
    assert extrair("seda preta e arta-preta")["cores"] == []
    assert extrair("hum preto")["cores"] == ["preto"]


def test_mina_sozinha_nao_e_nacao():
    assert extrair("Mina de ouro")["nacoes"] == []
    assert extrair("huma preta de Nação Mina")["nacoes"] == ["Mina"]


def test_sexo_ambos_so_com_pessoas_dos_dois_sexos():
    assert extrair("dous moleques e huma negrinha")["sexo"] == "ambos"
    assert extrair("duas pretas")["sexo"] == "f"
    assert extrair("huma preta que engomma roupa de homem e de Sra.")["sexo"] == "f"


def test_pre_nao_pega_preco_nem_preste():
    assert classificar({"texto": "PREÇO barato, vende-se"})[0] == "outro"
    assert classificar({"texto": "PRESTE atenção a esta preta"})[0] == "outro"


# --- c3: venda/compra/aluguel só com pessoa escravizável; condição "desconhecida" ---

def c3(texto, abertura):
    return extrair_anuncio({"texto": texto, "abertura": abertura})


def c4(texto, abertura):
    return extrair_anuncio({"texto": texto, "abertura": abertura})


def test_versao_c6():  # c6: recompensa, nação e idade aceitam mais erros de OCR (ver `_recompensa`, `_nacoes`, `ANOS`)
    assert VERSAO_CAMPOS == "c6"


@pytest.mark.parametrize("texto,abertura", [
    ("ALUGA-SE huma sala para escriptorio, na rua do Ouvidor n. 12.", "ALUGA-SE"),
    ("ALUGA-SE huma loja com armazem; na rua da Quitanda n. 4.", "ALUGA-SE"),
    ("ALUGA-SE huma casa terrea com quintal, propria para familia; na rua do Cattete n. 9.", "ALUGA-SE"),
    ("VENDE-SE a casa terrea da rua Larga n. 3, com sala e cozinha.", "VENDE-SE"),
    ("COMPRA-SE hum sitio perto da cidade; quem tiver diga na rua da Alfandega n. 8.", "COMPRA-SE"),
])
def test_c3_sem_pessoa_vira_outro(texto, abertura):
    r = c3(texto, abertura)
    assert (r["tipo"], r["procura"]) == ("outro", False)
    assert "pessoa" in r["evidencias"]["tipo"] and r["condicao"] is None


def test_c3_pessoa_so_no_anuncio_colado_depois_da_janela_vira_outro():
    colado = "VENDE-SE a casa terrea da rua Larga n. 3, com sala e cozinha. " + "x " * 100 + "huma preta de 20 annos"
    assert c3(colado, "VENDE-SE")["tipo"] == "outro"
    assert c3("VENDE-SE huma preta de 20 annos. " + "x " * 100, "VENDE-SE")["tipo"] == "venda"


def test_c3_senhora_portugueza_e_pessoa_livre():
    r = c3("ALUGA-SE huma senhora portugueza, para ama de casa de pouca familia; na rua do Hospicio n. 3.", "ALUGA-SE")
    assert r["tipo"] == "outro" and r["evidencias"]["tipo"]
    r = c3("ALUGA-SE huma menina portugueza para pagem de casa; na rua do Hospicio n. 3.", "ALUGA-SE")
    assert r["tipo"] == "outro" and "livre" in r["evidencias"]["tipo"]
    assert c3("PRECISA-SE huma ingleza para ama de crianças", "PRECISA-SE")["tipo"] == "outro"
    assert c3("ALUGA-SE huma moça livre que cozinha", "ALUGA-SE")["tipo"] == "outro"


def test_c3_marca_de_cor_vence_o_marcador_de_livre():
    r = c3("ALUGA-SE huma preta que falla francez, cozinha e lava", "ALUGA-SE")
    assert r["tipo"] == "aluguel"


def test_c3_aluga_preta_e_aluguel_de_mulher_com_condicao_desconhecida():
    r = c3("ALUGA-SE huma preta que cozinha e lava; na rua do Senado n. 5.", "ALUGA-SE")
    assert (r["tipo"], r["sexo"], r["condicao"]) == ("aluguel", "f", "desconhecida")


def test_c3_rapariga_e_ama_nao_dizem_a_condicao():
    r = c3("ALUGA-SE huma rapariga para casa de pouca familia; na rua do Lavradio n. 7.", "ALUGA-SE")
    assert (r["tipo"], r["sexo"], r["condicao"]) == ("aluguel_incerto", "f", "desconhecida")
    assert "sem marca de escravizado: rapariga" in r["evidencias"]["tipo"]
    r = c3("ALUGA-SE huma ama de leite do primeiro parto", "ALUGA-SE")
    assert (r["tipo"], r["condicao"]) == ("ama_de_leite", "desconhecida")


def test_c3_venda_de_negrinha_e_condicao_explicita_continua():
    r = c3("VENDE-SE huma linda negrinha de 13 annos", "VENDE-SE")
    assert (r["tipo"], r["sexo"]) == ("venda", "f")
    assert c3(T12, None)["condicao"] == "escravizado" and c3(T3, "ALUGA-SE")["condicao"] == "forro"


def test_c3_fuga_e_outro_nao_ganham_desconhecida():
    assert c3(T9, "N.")["condicao"] is None
    assert c3("ALUGA-SE huma sala", "ALUGA-SE")["condicao"] is None


# --- c4: aluguel só com marca explícita de escravizado na janela; senão aluguel_incerto ---

def test_c4_aluguel_sem_marca_e_incerto():
    r = c4("ALUGA-SE huma criada branca para casa de pouca familia", "ALUGA-SE")
    assert (r["tipo"], r["procura"], r["condicao"]) == ("aluguel_incerto", False, "desconhecida")
    assert "sem marca de escravizado: criada" in r["evidencias"]["tipo"]
    r = c4("PRECISA-SE de huma criada, livre ou escravo, que saiba cozinhar", "PRECISA-SE")
    assert (r["tipo"], r["procura"]) == ("aluguel_incerto", True)  # "livre ou escravo" não é marca


def test_c4_aluguel_com_marca_continua_aluguel():
    assert c4("ALUGA-SE um bom preto para todo o serviço; na rua da Guarda-Velha n. 35", "ALUGA-SE")["tipo"] == "aluguel"
    assert c4("ALUGA-SE huma preta que cozinha e lava", "ALUGA-SE")["tipo"] == "aluguel"
    assert c4("PRECISA-SE de huma criada preta, livre ou escravo", "PRECISA-SE")["tipo"] == "aluguel"  # marca fora da frase


def test_c4_anuncio_colado_nao_empresta_a_marca():
    colado = "ALUGA-SE huma sala para escriptorio na rua X. ESCRAVOS — Comprão-se escravos de ambos os sexos"
    assert c4(colado, "ALUGA-SE")["tipo"] in ("outro", "aluguel_incerto")
    assert c4(colado, "ALUGA-SE")["tipo"] != "aluguel"
    # pessoa sem marca no 1º anúncio, marca só no 2º colado: não é aluguel
    r = c4("ALUGA-SE huma criada para casa de familia; na rua X n. 3. VENDE-SE huma preta de 20 annos", "ALUGA-SE")
    assert r["tipo"] == "aluguel_incerto"
    # venda: o corte vale para a regra de pessoa do c3
    assert c4("VENDE-SE huma casa na rua Larga n. 3, com sala. COMPRA-SE huma preta de 20 annos", "VENDE-SE")["tipo"] == "outro"
    # "vende-se ou aluga-se": o 2º verbo é do mesmo anúncio
    assert c4("VENDE-SE ou ALUGA-SE huma preta de 20 annos", "VENDE-SE")["tipo"] == "venda"


def test_c4_resumo_conta_aluguel_incerto():
    r = resumir([{"tipo": "aluguel_incerto", "sexo": None, "idade_min": None, "nacoes": [], "nomes": [], "recompensa": False}])
    assert r["por_tipo"] == {"aluguel_incerto": 1} and "aluguel_incerto: 1" in formatar_resumo(r)


# --- c5: fuga só com pessoa; animal, papel, remédio e navio desaparecidos são "outro" ---

LIXO_C5 = [
    ("DESAPPARECEU", "Desapareceu da rua do Haddock Lobo n. 43 cão com os seguintes signaes: duas grandes malhas "
                     "brancas no lombo; quem o levar será gratificado.", "cao"),
    ("DESAPPARECEU", "Desapareceu, no dia 13 do corrente, um cachorro novo, raça Terra-Nova, pello escuro; "
                     "quem o achar queira levar á rua da Quitanda n. 9, que será bem recompensado.", "cachorro"),
    ("DESAPPARECEU", "DESAPPARECEU uma cautela do monte do soccorro n. 1234; pede-se a quem a achou o favor de "
                     "entrega-la na rua da Alfandega n. 8.", "cautela"),
    (None, "Este precioso medicamento cura tudo e faz desapparecer as molestias da pelle; vende-se na rua do "
           "Ouvidor n. 40.", "medicamento"),
    (None, "A guarnição do brigue fugio para terra no escaler, a nado, e foi apprehendida na praia.", "guarnicao"),
    (None, "FUGIO o cavallo ruço do Sr. Antonio; quem o apprehender será gratificado na rua do Lavradio n. 3.",
     "cavallo"),
]


@pytest.mark.parametrize("abertura,texto,palavra", LIXO_C5)
def test_c5_animal_papel_remedio_navio_e_outro(abertura, texto, palavra):
    r = extrair_anuncio({"texto": texto, "abertura": abertura})
    assert r["tipo"] == "outro"
    assert palavra in r["evidencias"]["tipo"] and r["evidencias"]["tipo"].startswith("sem pessoa")


def test_c5_cabra_animal_nao_e_pessoa():
    texto = ("DESENCAMINHOU-SE uma cabra branca; quem a levar á chacara n. 17, Cosme Velho, receberá alviçaras.")
    assert extrair_anuncio({"texto": texto})["tipo"] == "outro"
    assert extrair_anuncio({"texto": "42. " + texto})["tipo"] == "outro"


@pytest.mark.parametrize("texto,abertura", [
    ("FUGIO, no dia 25 de dezembro rua de Ma R", "FUGIO"),  # OCR ruim, sem pessoa: abertura basta
    ("dezappareceu hum muleque de Nação Benguella, por nome Antonio, de idade de 11 a 12 annos", None),
    ("DESAPPARECEU hum moleque de Nação Benguella, por nome Antonio, de idade de 11 a 12 annos", "DESAPPARECEU"),
    ("FUGIO hum escravo de nome Francisco, Angola", "FUGIO"),
    ("fugio uma cabra de nome Maria, de 20 annos, nação Mina", None),
    ("fugio uma cabra de nome Maria, de 20 annos, nação Mina", "FUGIO"),
])
def test_c5_fugas_reais_continuam_fuga(texto, abertura):
    assert extrair_anuncio({"texto": texto, "abertura": abertura})["tipo"] == "fuga"


def test_c5_marca_de_escravizado_vence_a_guarda():
    t = "VENDE-SE uma preta de 20 annos e um cavallo; na rua do Ouvidor n. 5."
    assert extrair_anuncio({"texto": t, "abertura": "VENDE-SE"})["tipo"] == "venda"


def test_c5_fuga_com_sinais_de_pessoa_mesmo_sem_a_palavra():
    """OCR estraga "escrava"; a fuga ainda tem idade, "sabe ler", "natural de" ou o dono."""
    casos = ["mudar de roupa quando anda fugido, sabe ler e escrever, e talvez se intitule livre; quem o apprehender levará á rua dos Benedictinos n. 1",
             "Fagio no dia 10 do proximo passado, esorava do Antonio Albino de Souza, quem a prender será gratificado",
             "FUGIDO em Fevereiro de 1854, da fazenda, o Antonio, natural da Parahyba, cheio de corpo, quem o apprehender receberá alviçaras"]
    for texto in casos:
        assert classificar({"texto": texto})[0] == "fuga", texto


def test_c5_estrada_nao_parece_escravo():
    texto = "Desappareceu a cautela do monte do soccorro; encarregado da estrada do Engenho Velho, receberá alviçaras"
    assert classificar({"texto": texto})[0] == "outro"


def test_c5_ama_de_leite_com_adjetivo_e_preto_livre():
    assert classificar({"texto": "PRECISA-SE alugar uma preta com bom leite, acabada de criar uma menina; na rua da Alfandega n. 256"})[0] == "ama_de_leite"
    tipo, _, motivo = _classificar({"texto": "ALUGA-SE um preto livre, perito cozinheiro e muito fiel; na rua do Sacadura n. 7"})
    assert tipo == "outro" and "livre" in motivo
    assert classificar({"texto": "ALUGA-SE um preto escravo, perito cozinheiro e muito fiel; na rua do Sacadura n. 7"})[0] == "aluguel"


def test_c5_guarda_de_animal_nao_derruba_ama_de_leite_com_anuncio_colado():
    """O OCR cola o anúncio vizinho (uma besta, uma cabra) na janela; a pessoa anunciada protege o anúncio."""
    assert classificar({"texto": "ALUGA-SE uma ama de leite ; na rua de D. Manoel n. 5 — VENDE-SE uma besta com arreios novos; na rua da Praia"})[0] == "ama_de_leite"
    assert classificar({"texto": "VENDE-SE uma excelente ama de leite com uma cria de dous mezes, que lava, engomma e cose; vende-se tambem um cachorro"})[0] == "ama_de_leite"
    assert classificar({"texto": "VENDE-SE uma cabra de raça, com abundancia de leite, por 60$; na rua do Cassia"})[0] == "outro"


def test_c5_cosmetico_e_remedio_com_leite_nao_sao_ama_de_leite():
    assert classificar({"texto": "COSMETICO Vende-se na rua do Rosario n. 25 — o leite de rosas da D. Felicidade embelleza as mulheres"})[0] == "outro"
    assert classificar({"texto": "O Arrobe Laffeeteur é precioso contra as molestias dos negros; um chancre no meato urinario, leite de vaca"})[0] == "outro"


def test_c5_auditoria_cachorrinha_cavalo_e_ama_colada():
    """Casos reais da auditoria dos anúncios mais típicos de cada tópico."""
    # fuga/perdido: só marca forte protege, a cor do bicho ("preta", "de cor preta") não
    assert classificar({"texto": "Perdeu-se, no dia 26 do corrente, da mão de um rapaz que conduzia presa a um cordel, uma cachorrinha preta, com a cauda e orelhas cortadas, que desappareceu da rua do Conde e acode pelo nome de Galatéa; quem a tiver achado queira entregar"})[0] == "outro"
    assert classificar({"texto": "DESAPPARECEU, no dia 28 do corrente, da cocheira da rua da Princeza, um peguira inteiro, de cor preta, com uma malha em um pé; quem o entregar será gratificado", "abertura": "DESAPPARECEU"})[0] == "outro"
    # venda: a pessoa antes do animal protege, o animal antes da cor não
    assert classificar({"texto": "23 Vende-se hum bom cavallo preto todo, sem manha; na rua do Piolho casa n. 118", "abertura": "N."})[0] == "outro"
    assert classificar({"texto": "VENDE-SE uma preta de 20 annos, que lava e cozinha, e tambem um cavallo russo; na rua do Ouvidor n. 40"})[0] == "venda"
    # ama de leite: a pessoa tem de estar na janela inicial, e "senhora ama de leite" é livre
    assert classificar({"texto": "RIQUISS muto finas, unico alimento que presentemente se acha, 70 por 70, escolhidas a vontade do comprador; na travessa do Guindaste n. 2, segundo andar; e nos domingos na rua Direita defronte do n. 45, varejo, uma ama de leite com sua cria"})[0] == "outro"
    assert classificar({"texto": "PRECISA-SE de hua senhora ama de leite, para criar huma criança de 9 mezes, que se queira transportar para Lisboa; para tratar, na rua do Hospicio n. 53", "abertura": "PRECISA-SE"})[0] == "outro"
    assert classificar({"texto": "ALUGA-SE uma parda de 18 annos, perfeita ama de leite, do primeiro parto; na rua de S. Pedro n. 314", "abertura": "ALUGA-SE"})[0] == "ama_de_leite"


def test_c5_documento_oficial_fumo_e_cavalo_mal_lido_nao_sao_pessoa():
    """Tipos de lixo achados na 2ª rodada da auditoria (anúncios típicos que a regra não tinha visto)."""
    assert classificar({"texto": "Extracto diario do dia 6 de dezembro de 1847. Na freguezia do Sacramento forão presos: Antonio José Ferreira, por desordem, e o escravo Francisco, Benguella, por proferir palavras obscenas", "abertura": "N."})[0] == "outro"
    assert classificar({"texto": "COPIA DO DECRETO. Hei por bem suspender do exercicio de juiz de paz da freguezia de Nossa Senhora da Guia a Bento José Veloso e mandá-lo responsabilisar"})[0] == "outro"
    assert classificar({"texto": "VENDE-SE na rua de S. José n. 155, rapé arêa e meio, pagando-se o premio que se convencionar, preta e princeza de superior qualidade", "abertura": "VENDE-SE"})[0] == "outro"
    assert classificar({"texto": "VENDE-SE hum cavalio castanho, de 7 palmos de alto, manço e muito bonito, proprio para huma carruagem; na rua Ourives n. 79", "abertura": "VENDE-SE"})[0] == "outro"
    assert classificar({"texto": "VENDE-SE hum preto de 20 annos, bom cozinheiro, sem vicios; na rua do Ouvidor n. 12 — vende-se tambem hum cavallo russo", "abertura": "VENDE-SE"})[0] == "venda"


# --- c6: recompensa, nação e idade com o OCR sujo (trechos reais do conjunto de desenvolvimento) ---

@pytest.mark.parametrize("texto", [
    "quem o condusir, e entregar a este novo so phorio, será recompençado do seu trabalho",
    "quem delle souber queira participar ao mesmo Carcereiro, que recompençarã o trabalho,",
    "terá à bondade do levar á rua da Caudelaria n. 18º, em freute à igreja , que será recempensado, . JOAO",
    "se lhe ficará obrigado, e se recompensari q seu trabalho.",
    "e levar à rua do Hospicio n. 16, será bem gralificado.",
    "quem o levar ao dito corinme será gratiticado. E",
    "será bem gratilicado, Eee A) 7 N",
    "Gratifi tin acima a quem appretender",
    "dando se contento para veuder-se; quem a apprebender 8 leva-la á rua de 8. José n. 60 será bom grati: ficado",
    "que será recom= pensados pelo trabalho", "será gratifi- cado", "receberá alvi- çaras", "promettendo-se até 100 18 de aiviçaras",
    "receberá boas tlviçaras em casa de Antonio", "dar-se-ha alvizaras", "receberá de premio 32:000",
])
def test_recompensa_com_ocr_sujo(texto):
    r = extrair(texto)
    assert r["recompensa"] is True and r["evidencias"]["recompensa"]


@pytest.mark.parametrize("texto", [
    "quem a achar será pago", "ficará muito obrigado a quem o trouxer", "pagamento do seu trabalho", "pago o seu trabalho",
    "quem a achar leve a rua do Ouvidor", "30$000 de pensão por mez",
])
def test_recompensa_nao_pega_pagamento_nem_obrigado(texto):
    assert extrair(texto)["recompensa"] is False


@pytest.mark.parametrize("texto,nacoes", [
    ("huma escrava por nome Maria\", Nação, Gangue: la, gorda, estatura", ["Gangue"]),
    ("fugio bum preto de Nação Songo, estatura ordinaria", ["Songo"]),
    ("hum preto de nação Mucena , de nome Francisco", ["Mucena"]),
    ("o preto Paula de nação Calango, estatara Vaixa", ["Calango"]),
    ("hum preto. Nação Banbuillo ;.eg= atura ordinaria", ["Banbuillo"]),
    ("por nome Just, de nação Cabiudu; * Votou huintá argola", ["Cabiudu"]),
    ("huma preta de Nação Nova", ["Nova"]),
    ("de Nação Portugueza, que sabe lavar", []), ("a Nação Ingleza", []), ("de nação Mina", ["Mina"]),
    ("Nação Mina", ["Mina"]), ("Nação de Mina", ["Mina"]), ("huma de nação, baixa e magra", []),
    ("Nação Sao", []),  # menos de 4 letras
    ("levou vestido calça e camisa de algodao de Minas, é crioulo", []),
    ("vestido de riscado de Mina, calças de brim", []), ("crioulo de Minas Geraes", []),
])
def test_nacao_citada_mesmo_desconhecida(texto, nacoes):
    assert extrair(texto)["nacoes"] == nacoes


@pytest.mark.parametrize("texto,faixa", [
    ("hum escravo, idade 20 e tantos annes; quitandeiro", (20, 29)),
    ("hum escravo, idade 20 e tantos; quitandeiro", (20, 29)),
    ("escravo com os signaes, idade poúto mais ou'menos 18\"annds;, Chamado Domingos", (18, 18)),
    ("preto Casimiro, idade pouco mais ou menos 18", (18, 18)), ("idade de 18", (18, 18)), ("idade 30", (30, 30)),
    ("um preto de nação Moçambique, de 30 à 40 unos, de altura regular", (30, 40)),
    ("hum pardo de nome Juão, idade 14 uunos , que paresse caboculo", (14, 14)),
    ("por nome Virgolino, de idade de 10 a 14 ennos, tem na cabeça", (10, 14)),
    ("hum criouloglesta Cidade , de nome Antonio, terá de idade 20 aunus, com hum risco", (20, 20)),
    ("20 e poucos annds", (20, 29)), ("terá 20 e tantos aunos", (20, 29)), ("tem 48 ou 50 aunos, é mu velhaco", (48, 50)),
    ("terá de idade 20 a 24 amos, levou vestido", (20, 24)), ("de idade 40 asno", (40, 40)),
    # o que não é idade
    ("Fugio ha 4 annos hum preto", (None, None)), ("ha 4 annos fugio", (None, None)),
    ("fugio ha 2 para 3 annos", (None, None)),
    ("no anno de 1843 fugio hum preto", (None, None)), ("30$000 de gratificação", (None, None)),
    ("idade 30$000 de gratificação", (None, None)), ("de idade, ha 8 dias fugio", (None, None)),
    ("idade 10 de Maio", (None, None)), ("20 avos do total", (None, None)), ("sua idade e 150", (None, None)),
    ("Fugio huma preta com 3 uns filhos", (None, None)), ("rua do Ouvidor 12 anos", (12, 12)),
])
def test_idade_com_ocr_sujo(texto, faixa):
    r = extrair(texto)
    assert (r["idade_min"], r["idade_max"]) == faixa
