from datetime import datetime

from hdb import relatorio
from hdb.banco import BancoMemoria

DADOS = {
    "gerado_em": "2026-11-11T10:30:00+00:00",
    "buscas": [{"termo": "escravo fugido", "bib": "364568_04", "acervo": "Jornal do Commercio",
                "total_servidor": 12345, "listadas": 1200, "primeira_coleta": "2026-10-01T09:00:00",
                "ultima_coleta": "2026-10-02T09:00:00", "paginas": {"ok": 1000, "erro": 3, "pendente": 197}}],
    "capturas": [{"quem": "ana", "ok": 100, "erros": {"captura": 2}, "captchas": 20, "segundos_medios": 31.5,
                  "primeira": "2026-10-01T09:00:00", "ultima": "2026-10-05T09:00:00"}],
    "ocr": {"motores": [{"motor": "tesseract-5", "paginas": 1500, "confianca_media": 88.25}],
            "acervos": [{"bib": "364568_04", "acervo": "Jornal do Commercio", "paginas": 1500,
                         "confianca_media": 88.2}]},
    "anuncios": [{"versao": "v2", "total": 4321, "largos": 10, "paginas": 900}],
    "campos": [{"versao": "c2", "total": 4321, "por_tipo": {"fuga": 3000, "venda": 1321},
                "por_sexo": {"m": 2000, "f": 1000}, "com_idade": 1500, "com_nome": 900, "com_recompensa": 2800,
                "nacoes": [{"nacao": "Benguela", "n": 120}]}],
    "panorama": {"periodos": [{"local": "RJ", "periodo": "1850 - 1859", "na_lista": 186, "com_bib": 180,
                               "com_erro": 6}],
                 "termos": [{"local": "RJ", "periodo": "1850 - 1859", "termo": "fugido", "acervos": 40,
                             "paginas": 9876}]},
}


def test_montar_tem_todas_as_secoes_e_numeros_formatados():
    texto = relatorio.montar(DADOS)
    for titulo in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7.", "## 8."):
        assert titulo in texto
    assert "11/11/2026 10:30" in texto and "https://memoria.bn.gov.br" in texto
    assert "12.345" in texto and "88,2" in texto and "31,5" in texto and "5,0 páginas por CAPTCHA" in texto
    assert "| `escravo fugido` | 364568_04 |" in texto
    assert "Benguela (120)" in texto and "fuga: 3.000" in texto
    assert "10.1015848/hh.v15i40.1904" not in texto and "10.15848/hh.v15i40.1904" in texto
    assert "pyHDB" in texto and "luizhenriquesoares" in texto


def test_limites_conhecidos_trazem_as_ressalvas_da_amostra():
    texto = relatorio.montar(DADOS)
    secao = texto.split("## 7. Limites conhecidos", 1)[1].split("## 8.", 1)[0]
    assert "não é aleatória" in secao and "vende-se uma preta" in secao
    assert "ordem de data" in secao and "1880–1889 há 1880, 1881 e 1885" in secao
    assert "Diário do Rio de Janeiro (1821)" in secao and "Diário Fluminense" in secao
    assert "criada" in secao and "`desconhecida`" in secao
    assert "LDA" in secao and "não fatos históricos" in secao


def test_montar_com_secoes_vazias():
    texto = relatorio.montar({"gerado_em": None, "buscas": [], "capturas": [], "ocr": {}, "anuncios": [],
                              "campos": [], "panorama": {"periodos": [], "termos": []}})
    assert "_Nada registrado ainda._" in texto
    assert "## 6." not in texto  # sem panorama, a seção some
    assert "## 7." in texto and "## 8." in texto
    assert "sem CAPTCHA registrado" in texto


def test_num_e_data():
    assert relatorio.num(1234567) == "1.234.567" and relatorio.num(12.34, 1) == "12,3"
    assert relatorio.num(None) == "–"
    assert relatorio.data("lixo") == "lixo"


def test_banco_memoria_relatorio():
    t = datetime(2026, 1, 1, 12, 0)
    banco = BancoMemoria(agora=lambda: t)
    banco.registrar_ocorrencia({"bib": "a", "acervo": "Acervo A", "termo": "fugido", "ocorrencia": 1,
                                "total_ocorrencias": 9, "ano": "1850", "pagina_fisica": "5"})
    pagina = banco.pagina("a", 5)
    ocr = {"texto": "x", "confianca": 90.0, "colunas": 2, "motor": "tess", "segundos": 2.0}
    banco.registrar_sucesso(pagina["id"], "ana", 10, 10, 10, ocr, 10.0, 1)
    banco.registrar_anuncios(pagina["id"], "v2", [{"ordem": 1, "largo": True}, {"ordem": 2, "largo": False}])
    anuncio = banco.anuncios(pagina["id"])[0]
    banco.registrar_campos("c2", [{"anuncio_id": anuncio["id"], "tipo": "fuga", "sexo": "m", "idade_min": 12,
                                   "nacoes": ["Mina"], "nomes": [], "recompensa": True}])
    banco.registrar_acervo_periodo("RJ", "1850 - 1859", 1, "A", bib="a")
    banco.registrar_acervo_periodo("RJ", "1850 - 1859", 2, "B", erro="x")
    banco.registrar_contagem("a", "fugido", 7)

    r = banco.relatorio()
    assert set(r) == {"gerado_em", "buscas", "capturas", "ocr", "anuncios", "campos", "panorama"}
    assert r["buscas"][0]["total_servidor"] == 9 and r["buscas"][0]["paginas"] == {"ok": 1}
    assert r["capturas"][0]["quem"] == "ana" and r["capturas"][0]["captchas"] == 1
    assert r["ocr"]["motores"][0]["confianca_media"] == 90.0 and r["ocr"]["acervos"][0]["bib"] == "a"
    assert r["anuncios"] == [{"versao": "v2", "total": 2, "largos": 1, "paginas": 1}]
    assert r["campos"][0]["por_tipo"] == {"fuga": 1} and r["campos"][0]["nacoes"] == [{"nacao": "Mina", "n": 1}]
    assert r["panorama"]["periodos"][0]["na_lista"] == 2 and r["panorama"]["periodos"][0]["com_erro"] == 1
    assert r["panorama"]["termos"][0]["paginas"] == 7
    assert "## 2." in relatorio.montar(r)
