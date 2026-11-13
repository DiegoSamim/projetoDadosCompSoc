import pytest

from hdb.banco import BancoMemoria
from hdb.campos import (VERSAO_CAMPOS, classificar, extrair, extrair_anuncio, formatar_resumo, linha_do_banco,
                        processar, resumir)

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


def test_condicao_livre_e_aluguel_de_sra_branca():
    assert extrair(T13)["condicao"] == "livre"
    assert classificar({"texto": T13, "abertura": "ALUGA-SE"}) == ("aluguel", False)


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
