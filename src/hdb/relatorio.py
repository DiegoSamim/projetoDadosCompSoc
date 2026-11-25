"""Relatório metodológico: um Markdown que diz como o corpus foi formado, a partir dos números do banco."""
from datetime import datetime

ENDERECO = "https://memoria.bn.gov.br"
VAZIO = "_Nada registrado ainda._"

REGRAS_BUSCA = (
    "A HDB devolve **páginas**, não anúncios: cada ocorrência é uma página em que o termo aparece.",
    "A busca é por **palavra exata** (ignora maiúsculas e acentos); `*` no fim da palavra aceita variações.",
    "Aspas duplas buscam a **frase exata**; sem aspas, várias palavras devem estar na mesma página.",
    "Não há operadores OU nem NÃO.",
    "Palavras muito comuns (como `de`) são ignoradas pela HDB e devolvem 0 resultados.",
)

LIMITES = (
    "O OCR erra letras (e às vezes palavras inteiras); a confiança é a média do Tesseract, não uma medida de acerto.",
    "A separação em anúncios e a extração de campos (tipo, sexo, idade, nação etc.) são heurísticas, "
    "sem revisão manual.",
    "A HDB conta **páginas** com o termo, não anúncios nem ocorrências dentro da página.",
    "As contagens do panorama valem para o **acervo inteiro**, não só para a década pedida; "
    "acervos que cobrem mais de uma década aparecem sinalizados.",
    "Não há rótulos manuais: nenhum campo foi conferido por pessoas, então não há taxa de acerto medida.",
    "A amostra não é aleatória: ela vem de páginas que contêm frases de busca (ex.: \"vende-se uma preta\"). "
    "Mostra os anúncios que essas frases acham, então as proporções (tipo, sexo) não representam o jornal "
    "inteiro. A redação dos anúncios mudou com o tempo, e algumas frases deixam de existir depois de certa data.",
    "A listagem de cada busca vem em ordem de data, e só as primeiras páginas foram listadas. Por isso alguns "
    "anos ficam sem páginas (ex.: no Jornal do Commercio de 1880–1889 há páginas de 1880 a 1886, e nada de 1887 e 1888, porque "
    "a listagem foi interrompida pelo servidor da BN antes de chegar a esses anos).",
    "Antes de 1831 a amostra vem sobretudo do Diário do Rio de Janeiro (1821) e do Diário Fluminense; os demais "
    "períodos vêm do Jornal do Commercio. Parte da diferença entre períodos pode ser diferença de jornal.",
    "Nos tipos aluguel, compra e venda, nem todo anúncio é de pessoa escravizada: \"criada\", \"rapariga\" e "
    "\"ama\" não dizem a condição. Quando o texto não diz, a condição jurídica fica registrada como "
    "`desconhecida`. A conferência manual por amostra está planejada, mas ainda não foi feita.",
    "O OCR do Jornal do Commercio dos anos 1860–1880 é pior (confiança média perto de 63 a 67) e deixa palavras "
    "quebradas. Anúncios vizinhos às vezes saem colados em um só.",
    "Os tópicos (LDA) são padrões de palavras, não fatos históricos. Eles dependem do número de tópicos escolhido "
    "e da leitura que se faz de cada grupo.",
)

CREDITOS = (
    "pyHDB (Eric Brasil, licença MIT): BRASIL, Eric. pyHDB – Ferramenta Heurística para a Hemeroteca Digital "
    "Brasileira. *História da Historiografia*, v. 15, n. 40, p. 186–217, 2022. "
    "DOI 10.15848/hh.v15i40.1904. https://github.com/ericbrasiln/pyHDB",
    "A ideia de extrair campos dos anúncios é inspirada em https://github.com/luizhenriquesoares/hemeroteca-digital "
    "(sem código reaproveitado).",
)


def num(valor, casas=0):
    """Número no formato pt-BR (milhar com ponto, decimal com vírgula); "–" se nulo."""
    if valor is None:
        return "–"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def data(iso):
    """Data e hora legíveis (dd/mm/aaaa hh:mm) de um texto ISO; "–" se nulo."""
    if not iso:
        return "–"
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(iso)[:16]


def tabela(cabecalho, linhas):
    """Tabela Markdown; texto de aviso se não há linhas."""
    if not linhas:
        return VAZIO
    corpo = ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho), *corpo])


def _contagens(d):
    return ", ".join(f"{k}: {num(v)}" for k, v in sorted(d.items(), key=lambda x: -x[1])) or "–"


def _cabecalho(dados):
    regras = "\n".join(f"- {r}" for r in REGRAS_BUSCA)
    return (f"# Relatório metodológico da coleta\n\nGerado em {data(dados.get('gerado_em'))}. "
            f"Fonte: Hemeroteca Digital Brasileira, {ENDERECO}.\n\n"
            f"## 1. Regras da busca da HDB\n\n{regras}")


def _corpus(dados):
    linhas = []
    for b in dados.get("buscas") or []:
        p = b.get("paginas") or {}
        linhas.append((f"`{b['termo']}`", b["bib"], b.get("acervo") or "–", num(b.get("total_servidor")),
                       num(b["listadas"]), num(p.get("ok", 0)), num(p.get("erro", 0)),
                       data(b.get("primeira_coleta")), data(b.get("ultima_coleta"))))
    cab = ("Termo", "Acervo (bib)", "Nome", "No servidor", "Listadas", "Capturadas", "Com erro",
           "1ª coleta", "Última coleta")
    return ("## 2. Como o corpus foi formado\n\n"
            "Para cada termo e acervo: quantas ocorrências a HDB informa, quantas foram listadas por nós e "
            f"quantas páginas já foram capturadas.\n\n{tabela(cab, linhas)}")


def _capturas(dados):
    caps = dados.get("capturas") or []
    linhas = [(c["quem"], num(c["ok"]), num(c["captchas"]), _contagens(c.get("erros") or {}),
               num(c.get("segundos_medios"), 1), f"{data(c.get('primeira'))} a {data(c.get('ultima'))}")
              for c in caps]
    oks, captchas = sum(c["ok"] for c in caps), sum(c["captchas"] for c in caps)
    por_captcha = f"{num(oks / captchas, 1)} páginas por CAPTCHA" if captchas else "sem CAPTCHA registrado"
    cab = ("Quem", "Páginas ok", "CAPTCHAs", "Erros por etapa", "Segundos médios", "Período")
    return (f"## 3. Captura\n\nUma pessoa resolve cada CAPTCHA; a ferramenta não o contorna. "
            f"Total: {num(oks)} páginas ok, {num(captchas)} CAPTCHAs ({por_captcha}).\n\n{tabela(cab, linhas)}")


def _ocr(dados):
    ocr = dados.get("ocr") or {}
    motores = tabela(("Motor", "Páginas", "Confiança média"),
                     [(m["motor"], num(m["paginas"]), num(m.get("confianca_media"), 1))
                      for m in ocr.get("motores") or []])
    acervos = tabela(("Acervo (bib)", "Nome", "Páginas", "Confiança média (leitura atual)"),
                     [(a["bib"], a.get("acervo") or "–", num(a["paginas"]), num(a.get("confianca_media"), 1))
                      for a in ocr.get("acervos") or []])
    return f"## 4. Texto (OCR)\n\n{motores}\n\n{acervos}"


def _anuncios_e_campos(dados):
    anuncios = tabela(("Versão da separação", "Anúncios", "Largos (cruzam colunas)", "Páginas"),
                      [(a["versao"], num(a["total"]), num(a["largos"]), num(a["paginas"]))
                       for a in dados.get("anuncios") or []])
    partes = [f"## 5. Anúncios e campos\n\n{anuncios}"]
    for c in dados.get("campos") or []:
        nacoes = ", ".join(f"{n['nacao']} ({num(n['n'])})" for n in c.get("nacoes") or []) or "–"
        partes.append(
            f"### Campos, versão {c['versao']}\n\n{num(c['total'])} anúncios.\n\n"
            f"- Tipo: {_contagens(c.get('por_tipo') or {})}\n"
            f"- Sexo: {_contagens(c.get('por_sexo') or {})}\n"
            f"- Com idade: {num(c['com_idade'])}; com nome: {num(c['com_nome'])}; "
            f"com recompensa: {num(c['com_recompensa'])}\n"
            f"- Nações mais comuns: {nacoes}")
    if not dados.get("campos"):
        partes.append("Campos: " + VAZIO)
    return "\n\n".join(partes)


def _panorama(dados):
    pan = dados.get("panorama") or {}
    if not pan.get("periodos") and not pan.get("termos"):
        return None
    periodos = tabela(("Local", "Período", "Periódicos na lista", "Com código (bib)", "Com erro"),
                      [(p["local"], p["periodo"], num(p["na_lista"]), num(p["com_bib"]), num(p["com_erro"]))
                       for p in pan.get("periodos") or []])
    termos = tabela(("Local", "Período", "Termo", "Acervos com o termo", "Soma de páginas"),
                    [(t["local"], t["periodo"], f"`{t['termo']}`", num(t["acervos"]), num(t["paginas"]))
                     for t in pan.get("termos") or []])
    return f"## 6. Panorama de acervos\n\n{periodos}\n\n{termos}"


def montar(dados):
    """O relatório em Markdown a partir do dict de `banco.relatorio()`."""
    limites = "\n".join(f"- {t}" for t in LIMITES)
    creditos = "\n".join(f"- {t}" for t in CREDITOS)
    secoes = [_cabecalho(dados), _corpus(dados), _capturas(dados), _ocr(dados), _anuncios_e_campos(dados),
              _panorama(dados), f"## 7. Limites conhecidos\n\n{limites}", f"## 8. Créditos\n\n{creditos}"]
    return "\n\n".join(s for s in secoes if s) + "\n"
