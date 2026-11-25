import importlib.util
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts" / "resumo_dados.py"
spec = importlib.util.spec_from_file_location("resumo_dados", ARQUIVO)
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)
afirmacoes = rd.afirmacoes


def anuncio(i, periodo, tipo, **kw):
    return {"id": i, "periodo_legal": periodo, "ano": 1850, "c_tipo": tipo, "c_sexo": kw.get("sexo"),
            "c_idade_min": kw.get("idade"), "c_nacoes": kw.get("nacoes"), "c_recompensa": kw.get("recompensa", False)}


def _quadro_resultados():
    return {}


def _quadro_simulado():
    p = ["antes de 1831", "1831–1850", "1850–1871", "1871–1888"]
    cel = lambda vs: {q: {"n": 100, "n_ef": 100.0, "valor": v, "baixo": v - 1, "alto": v + 1} for q, v in zip(p, vs)}
    d = {b: (-30.0, -33.0, -27.0) for b in p[:-1]}
    r = {"bruta": cel([60, 50, 40, 30]), "jc": cel([60, 50, 40, 30]), "ajustada": cel([60, 50, 40, 30]),
         "dif": {"bruta": d, "jc": d, "ajustada": d}, "tendencia": {"bruta": (1e-6, 0.0), "jc": (1e-6, 0.0)}}
    return afirmacoes.quadro({i: r for i in range(1, 10)})


DADOS = {
    "gerado_em": "2026-11-25",
    "versoes": {"campos": "c5", "corpus": "corp3", "topicos": "t5"},
    "quadro": None,
    "anuncios": [
        anuncio(1, "1831–1850 (Feijó → Eusébio)", "fuga", sexo="m", idade=20, nacoes=["Mina"], recompensa=True),
        anuncio(2, "1831–1850 (Feijó → Eusébio)", "fuga", sexo="m", nacoes=["Mina", "Congo"]),
        anuncio(3, "1871–1888 (Ventre Livre → Áurea)", "ama_de_leite", sexo="f", idade=18),
        anuncio(4, "1871–1888 (Ventre Livre → Áurea)", "outro"),
    ],
    "topicos": {"palavras": {0: ["leite", "ama", "meses", "carinhosa"], 1: ["xx", "yy"]},
                "mistura": {1: {0: 0.2, 1: 0.8}, 3: {0: 0.9, 1: 0.1}}},
    "paginas_por_ano": [{"acervo": "Jornal do Commercio", "ano": a, "n": 10} for a in range(1880, 1887)]
                       + [{"acervo": "Jornal do Commercio", "ano": a, "n": 3} for a in range(1821, 1880)],
}


def test_montar_tem_versoes_tabelas_e_ressalvas():
    t = rd.montar({**DADOS, "quadro": _quadro_simulado()})
    assert "campos `c5`, corpus `corp3`, tópicos `t5`" in t and "2026-11-25" in t
    assert "| 1831–1850 |" in t and "| **Total** |" in t
    assert "Ama de leite" in t and "acompanham o tipo" in t and "não mostram mudança" in t
    assert "## Quadro de afirmações" in t and "A recompensa nas fugas diminui" in t and "**sustentada**" in t
    assert t.index("## Os temas") < t.index("## Quadro de afirmações") < t.index("## Sinais principais")
    assert "50%" in t  # 1 de 2 fugas com recompensa em 1831–1850
    assert "Mina (100%)" in t
    assert "## Os 3 limites principais" in t and "Amostra por busca" in t


def test_anos_sem_pagina_mostram_1887_e_1888():
    t = rd.montar(DADOS)
    assert "**1887**" in t and "**1888**" in t
    linha = [l for l in t.splitlines() if l.startswith("**Anos sem nenhuma página")][0]
    assert "1887" in linha and "1886" not in linha and "1885" not in linha


def test_montar_sem_dados_nao_falha():
    t = rd.montar({"versoes": {}, "anuncios": [], "topicos": {}, "paginas_por_ano": []})
    assert "_Sem dados._" in t and "# Resumo dos dados" in t
    assert "## Quadro de afirmações\n\n_Sem dados._" in t


def test_ler_com_banco_simulado(monkeypatch):
    monkeypatch.setattr(rd.medidas, "carregar", lambda banco, config: None)
    monkeypatch.setattr(rd.medidas, "calcular", lambda df: _quadro_resultados())
    monkeypatch.setattr(rd.pontos_mudanca, "calcular_pontos", lambda df: {})
    class Consulta:
        def __init__(self, tabela, dados): self.t, self.d, self.ini = tabela, dados, 0
        def select(self, *a): return self
        def eq(self, *a): return self
        def in_(self, *a): return self
        def order(self, *a, **k): return self
        def range(self, i, j): self.ini, self.fim = i, j; return self
        def execute(self):
            class R: pass
            r = R(); r.data = self.d[self.ini:self.fim + 1]; return r

    tabelas = {"anuncios_completos": [anuncio(1, "1831–1850 (x)", "fuga")],
               "topico_palavras": [{"topico": 0, "palavra": "leite", "peso": 1}],
               "anuncio_topicos": [{"anuncio_id": 1, "topico": 0, "proporcao": 1.0}],
               "acervos": [{"bib": "b", "nome": "Jornal"}],
               "paginas": [{"id": 1, "bib": "b", "ano": 1850}, {"id": 2, "bib": "b", "ano": None}]}

    class Cli:
        def table(self, nome): return Consulta(nome, tabelas[nome])

    class Banco:
        cliente = Cli()

    d = rd.ler(Banco())
    assert d["paginas_por_ano"] == [{"acervo": "Jornal", "ano": 1850, "n": 1}]
    assert d["topicos"]["mistura"] == {1: {0: 1.0}} and d["topicos"]["palavras"] == {0: ["leite"]}
    assert d["versoes"]["campos"] and len(d["anuncios"]) == 1
    assert len(d["quadro"]) == 9 and d["quadro"][0]["veredito"] == "frágil"
