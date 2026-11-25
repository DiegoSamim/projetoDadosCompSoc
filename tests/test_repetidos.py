import pandas as pd

from hdb import repetidos as r

BASE = ("Fugiu da casa de seu senhor o escravo Joaquim, crioulo de cor preta, com 20 annos de idade, "
        "estatura regular, sem barba, levou calça de algodão e camisa de riscado; quem o apprehender "
        "leve-o à rua do Ouvidor que será bem recompensado")
OUTRO = ("Vende-se uma preta que cozinha lava e engomma perfeitamente, sem vicios nem achaques, de bom "
         "genio e propria para casa de familia, trata-se na rua da Quitanda no armazem numero tres")


def linha(i, texto, ed, bib="1", ano=1850, **kw):
    return {"id": i, "texto": texto, "bib": bib, "ano": ano, "edicao": str(ed), "pagina_fisica": 1, "ordem": 1,
            "periodo_legal": "1850–1871", "c_tipo": "fuga", **kw}


def df(*linhas):
    return pd.DataFrame(list(linhas))


def test_normalizar():
    assert r.normalizar("  Fugiu, a ESCRAVA Maria! 25 annos; São-Paulo 1850x ") == "fugiu a escrava maria annos sao paulo 1850x"


def test_tres_edicoes_seguidas_agrupam():
    ag = r.agrupar(df(linha(3, BASE, 12), linha(1, BASE, 10), linha(2, BASE, 11), linha(4, OUTRO, 11)))
    g = ag.set_index("id")
    assert g.loc[[1, 2, 3], "grupo"].nunique() == 1
    assert g.loc[4, "grupo"] != g.loc[1, "grupo"]
    assert list(g[g["representante"]].index.sort_values()) == [1, 4]
    assert g.loc[1, "grupo"] == 1


def test_jornais_ou_anos_diferentes_nao_agrupam():
    ag = r.agrupar(df(linha(1, BASE, 10), linha(2, BASE, 11, bib="2"), linha(3, BASE, 12, ano=1851)))
    assert ag["grupo"].nunique() == 3 and ag["representante"].all()


def test_janela():
    assert r.agrupar(df(linha(1, BASE, 10), linha(2, BASE, 41)))["grupo"].nunique() == 2
    assert r.agrupar(df(linha(1, BASE, 10), linha(2, BASE, 40)))["grupo"].nunique() == 1


def test_ocr_com_palavras_trocadas_agrupa():
    ruido = BASE.replace("crioulo", "crioalo").replace("algodão", "algodao x")
    ag = r.agrupar(df(linha(1, BASE, 10), linha(2, ruido, 12)), limiar=0.6)
    assert ag["grupo"].nunique() == 1


def test_texto_curto_nao_agrupa():
    curto = "Fugiu escravo Joaquim rua do Ouvidor"
    assert r.agrupar(df(linha(1, curto, 10), linha(2, curto, 11)))["grupo"].nunique() == 2


def test_mesmo_modelo_corpo_diferente_fica_abaixo_do_limiar():
    a = "Fugiu o escravo Antonio de nação Benguela, alto e magro, com falta de dentes, levou calça azul; gratifica-se bem a quem o levar a rua Direita"
    b = "Fugiu o escravo Manoel de nação Congo, baixo e gordo, com marcas de chicote nas costas, levou jaqueta branca; gratifica-se bem a quem o levar a rua Direita"
    p = r.pares_candidatos(df(linha(1, a, 10), linha(2, b, 11)), 0.0)
    assert len(p) == 0 or p["similaridade"].iloc[0] < 0.6
    assert r.agrupar(df(linha(1, a, 10), linha(2, b, 11)))["grupo"].nunique() == 2


def test_pares_campos_e_determinismo():
    d = df(linha(1, BASE, 10), linha(2, BASE, 14), linha(3, OUTRO, 12))
    p = r.pares_candidatos(d)
    assert list(p.columns) == ["id_a", "id_b", "similaridade", "dist_edicao", "mesmo_ano_edicao"]
    assert len(p) == 1 and p.iloc[0]["similaridade"] == 1.0 and p.iloc[0]["dist_edicao"] == 4
    assert r.agrupar(d).equals(r.agrupar(d.sample(frac=1, random_state=1)).sort_values("id").reset_index(drop=True)
                               .loc[:, d.columns.tolist() + ["grupo", "representante"]])


def test_resumo():
    d = df(linha(1, BASE, 10), linha(2, BASE, 11), linha(3, BASE, 12, c_tipo="venda"), linha(4, OUTRO, 11, bib="2"))
    res = r.resumo(r.agrupar(d))
    assert (res["anuncios"], res["grupos"], res["removiveis"]) == (4, 2, 2)
    assert res["perde_pct"] == 50.0
    pb = res["por_bib"].set_index("bib")
    assert pb.loc["1", "anuncios"] == 3 and pb.loc["1", "grupos"] == 1 and round(pb.loc["1", "perde_pct"], 1) == 66.7
    pt = res["por_tipo"].set_index("c_tipo")
    assert pt.loc["fuga", "grupos"] == 2 and pt.loc["venda", "anuncios"] == 1
