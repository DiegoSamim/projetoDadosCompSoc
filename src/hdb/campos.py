"""Classifica os anúncios e extrai campos (sexo, idade, nação, cor, nome, ofício, recompensa, valor, endereço).

Funções puras sobre o texto de OCR de jornais de 1820-1889 (grafia antiga, erros de OCR). É heurístico:
cada campo vem com o trecho que o justificou (`evidencias`), para conferir olhando o texto.
"""
import re
import unicodedata
from collections import Counter

from hdb.config import LOTE_CAMPOS, VERSAO_CAMPOS
from hdb.anuncios import achar_abertura, achar_numeracao, distancia, e_secao

TIPOS = ("fuga", "venda", "compra", "aluguel", "ama_de_leite", "outro")

IDADE_MAXIMA = 90
NACAO_ERROS = 1  # erros de OCR tolerados no nome de uma nação
NACAO_LETRAS_MINIMAS = 6  # só nomes com pelo menos isto de letras toleram erro

# --- listas de palavras (tudo em minúsculas e sem acento: é como o texto é comparado) ---

ABERTURA_TIPO = {
    "PRECISA-SE": "precisa", "VENDE-SE": "venda", "VENDEM-SE": "venda", "ENDE-SE": "venda",
    "ALUGA-SE": "aluguel", "ALUGAM-SE": "aluguel", "OFFERECE-SE": "aluguel",
    "COMPRA-SE": "compra", "COMPRAM-SE": "compra",
    "FUGIO": "fuga", "FUGIU": "fuga", "EVADIO-SE": "fuga", "DESAPPARECEU": "fuga",
}
VERBOS = (  # (regex, tipo): o verbo mais cedo no texto vale quando não há abertura conhecida
    (r"\bvend(?:e|em)\s*-?\s*se\b", "venda"), (r"\bcompr(?:a|am)\s*-?\s*se\b", "compra"),
    (r"\balug(?:a|am)\s*-?\s*se\b", "aluguel"), (r"\bprecis(?:a|am|ao)\s*-?\s*se\b", "precisa"),
    (r"^\W*pre\W+(?:\w{0,2}ugar|gar)\b", "precisa"),  # "PRE (gar uma preta": PRECISA-SE alugar destruído pelo OCR; "preço" não casa
    (r"\bpara\s+serem?\s+vendid", "venda"), (r"\breceb(?:e|em|er)\b[^.;]{0,30}\bescrav", "venda"),  # consignação
    (r"\boffere[cs]\w*\s+pel[ao]s?\b", "venda"),  # "a pessoa que offereceu pela preta 4204000"
)
PALAVRAS_FUGA = {
    "fugio", "fugiu", "fugirao", "fugiram", "fugido", "fugida", "fugidos", "fugidas", "evadio", "evadiu",
    "desappareceu", "dezappareceu", "desapareceo", "desapareceu", "ausentou", "alvicaras", "alvicara",
}
FUGA_FUZZY = ("desappareceu", "dezappareceu", "desapareceo")  # OCR estraga ("dezapateceu"): 2 erros
TITULOS_FUGA = ("ESCRAVOS FUGIDOS",)

PESSOAS = {  # palavra de pessoa (sem plural) -> sexo da pessoa anunciada (None: não diz)
    "preto": "m", "pretinho": "m", "pardo": "m", "crioulo": "m", "crioulinho": "m", "escravo": "m",
    "moleque": "m", "molecote": "m", "negrinho": "m", "mulato": "m", "negro": "m", "cativo": "m",
    "captivo": "m", "liberto": "m", "fulo": "m", "africano": "m", "rapaz": "m", "menino": "m", "criado": "m",
    "preta": "f", "pretinha": "f", "parda": "f", "crioula": "f", "crioulinha": "f", "escrava": "f",
    "negrinha": "f", "molecota": "f", "moleca": "f", "mulata": "f", "negra": "f", "cativa": "f", "captiva": "f",
    "forra": "f", "liberta": "f", "fula": "f", "africana": "f", "rapariga": "f", "ama": "f", "mucama": "f",
    "menina": "f", "criada": "f",
    "cabra": None, "bocal": None, "ladino": None, "ladina": None,
}
# "preta" de seda ou "escravo" passageiro de navio não são a pessoa anunciada: só conta palavra de pessoa com
# contexto de pessoa. Contexto: artigo, numeral, quantificador ou possessivo até 2 palavras antes; outra
# palavra de pessoa já aceita logo antes; ou, logo depois, idade, "por nome", "de nação"...
DETERMINANTES = {
    "hum", "huma", "um", "uma", "uns", "umas", "o", "a", "os", "as", "dous", "dois", "duas", "douz", "tres",
    "quatro", "cinco", "alguns", "algumas", "seu", "sua", "seus", "suas", "da", "do", "das", "dos", "pela",
    "pelo", "pelas", "pelos", "esse", "essa", "este", "esta", "outro", "outra", "outros", "outras", "meu",
    "minha", "linda", "lindas", "lindo", "lindos", "boa", "boas", "bom", "bons", "bonita", "bonito", "nova",
    "novo", "moca", "moco", "se", "receber", "comprar", "vender", "alugar",
}
CONTEXTO_DEPOIS = re.compile(
    r"\b(?:de\s+\d{1,2}\b|\d{1,2}\s*a[nu]{1,2}[o0]s|por\s+nome|de\s+nome|de\s+nacao|nacao|que\s+sab[eh]|"
    r"que\s+tem|official\s+de)")
SRA = re.compile(r"\b(?:huma|uma)\s+(?:sra|senhora)\b")  # "ALUGA-SE huma Sra. branca": gente, sem sexo próprio
NAVIO = re.compile(r"\bequip\w*\.?\s*\d|\bpassag\w*\.?\s*\d|\bcarga\b")  # movimento de porto, "1 escravo" passageiro
ACHAR = re.compile(r"\bquem\s*[oa]?\s*(?:o\s+|a\s+)?(?:achar|apprehender|pegar|prender|capturar|trouxer)")
LEITE = re.compile(r"\bama\s+(?:de|com)\s+leite\b|\b(?:com|de)\s+leite\b")
PEDIDO = re.compile(r"\b(alugar|alugarem|alugue|comprar|comprarem)\b")
COR_LIVRE = {"fula", "fulo", "bocal", "ladino", "ladina", "africano", "africana"}  # qualidades que valem sem artigo

CORES = {  # palavra (sem plural) -> forma padronizada
    "preto": "preto", "preta": "preto", "pretinho": "preto", "pretinha": "preto",
    "pardo": "pardo", "parda": "pardo", "pardinho": "pardo", "pardinha": "pardo",
    "crioulo": "crioulo", "crioula": "crioulo", "crioulinho": "crioulo", "crioulinha": "crioulo",
    "cabra": "cabra", "cabrinha": "cabra", "cabrinho": "cabra",
    "fula": "fula", "fulo": "fula",  # "fula" fica assim: é também nome de povo, não só cor
    "mulato": "mulato", "mulata": "mulato", "mulatinho": "mulato", "mulatinha": "mulato",
    "negro": "negro", "negra": "negro", "negrinho": "negro", "negrinha": "negro",
    "bocal": "boçal", "ladino": "ladino", "ladina": "ladino", "africano": "africano", "africana": "africano",
}

NACOES = {  # forma padronizada -> grafias (sem acento) além dela mesma
    "Angola": ("angola",), "Benguela": ("benguela", "benguella"), "Cabinda": ("cabinda",),
    "Cabundá": ("cabunda",), "Congo": ("congo",), "Mina": ("mina",), "Monjolo": ("monjolo",),
    "Moçambique": ("mocambique", "mossambique", "mozambique"), "Rebolo": ("rebolo",), "Nagô": ("nago",),
    "Cassange": ("cassange", "cassanje", "cassangue"), "Ganguela": ("ganguela",), "Calabar": ("calabar",),
    "Quilimane": ("quilimane",), "Inhambane": ("inhambane",), "Mofumbe": ("mofumbe",),
    "Haussá": ("haussa", "hausa"), "Gabão": ("gabao",), "Moange": ("moange",), "Ambaca": ("ambaca",),
    "Libolo": ("libolo",),
}
NACAO_FORMAS = {forma: nome for nome, formas in NACOES.items() for forma in formas}
NACAO_AMBIGUAS = {"mina"}  # só vale com inicial maiúscula
NAO_NACOES = {"rebelo", "angela", "angelo"}  # nomes de gente a 1 erro de uma nação

OFICIOS = (  # (regex, forma padronizada) sobre o texto sem acento
    (r"cozinheir[oa]s?", None), (r"lavadeiras?", "lavadeira"), (r"engom+adeiras?", "engommadeira"),
    (r"costureiras?", "costureira"), (r"ama\s+de\s+leite", "ama de leite"), (r"ama\s+sec+a", "ama secca"),
    (r"alfaiates?", "alfaiate"), (r"sapateiros?", "sapateiro"), (r"marceneiros?", "marceneiro"),
    (r"carpinteiros?", "carpinteiro"), (r"pedreiros?", "pedreiro"), (r"serralheiros?", "serralheiro"),
    (r"serradors?|serradores", "serrador"), (r"quitandeir[oa]s?", None), (r"pagens?", "pagem"),
    (r"copeiros?", "copeiro"), (r"cocheiros?", "cocheiro"), (r"mucamas?", "mucama"),
)
OFFICIAL_DE = re.compile(r"\bof+i[cs]i?al\s+de\s+([a-z]{4,})")
NAO_OFICIOS = {"justica", "fazenda", "marinha", "secretaria", "diligencias", "gabinete"}

RECOMPENSA = re.compile(r"gratific|alvicara|alvissara|\bpremio|recompensa")
VALOR = re.compile(r"(?<![\w:$])(\d{1,3}(?::\d{3})+(?:\$\d{1,3})?|\d{1,4}\$\d{0,3}|\d{1,3}s)(?!\w)")
ENDERECO = re.compile(  # até 45 caracteres entre o logradouro e o "n. 12"; "S." (santo) não fecha a frase
    r"\b(?:rua|largo|beco|praia|travessa|campo|praca|ladeira)\b(?:[^;.:\n]|\bs\.){0,45}?\bn\b[.,]?\s*[º°o]?\.?\s*\d+")

TEMPO_ANTES = re.compile(r"\b(?:ha|a|faz|fazem|desde|cerca\s+de|perto\s+de)\s+$")  # "ha 2 para 3 annos": tempo, não idade
ANOS = r"a[nu]{1,2}[o0]s\b"
IDADE_TANTOS = re.compile(rf"(?<![\d:$])(\d{{1,2}})\s+e\s+(?:tantos|poucos)\s+{ANOS}")
IDADE = re.compile(rf"(?<![\d:$.])(\d{{1,2}})(?:\s*(?:a|para|ate|ou|e)\s*(\d{{1,2}}))?\s*{ANOS}")
IDADE_OUTRO = re.compile(  # "hum de 10 à 12 annos, outro de 16 a 18": a 2ª idade vem sem "annos"
    r"\b(?:outr[oa]s?|ou[a-z]{2,3})\s+de\s+(\d{1,2})(?:\s*(?:a|para)\s*(\d{1,2}))?(?![\d:$])")

NOME = re.compile(
    r"(?i:\b(?:por\s+nome|de\s+nome|chamad[oa]|nome))\s+"
    r"([A-ZÀ-Ý][^\W\d_]+(?:\s+[A-ZÀ-Ý][^\W\d_]+)?)")
NAO_NOMES = {"nacao", "sr", "senhor", "sra", "senhora", "rua", "largo", "beco", "praia", "travessa"}

FORRO = re.compile(r"\b(?:forr[oa]s?|libert[oa]s?)\b")
ESCRAVIZADO = re.compile(r"\b(?:escrav[oa]s?|cativ[oa]s?|captiv[oa]s?)\b")
LIVRE = re.compile(  # "calças brancas" não é gente branca; "livre de achaques" não é condição
    r"\blivres?\b(?!\s+de\b)|\bfilh[oa]s?\s+das\s+ilhas\b|\bilheu\b"
    r"|\b(?:sra|senhora|moca|mulher|homem|rapaz|menina|menino)\.?\s+branc[oa]\b|\bhuma?\s+branc[oa]\b")


def _simples(texto):
    """Minúsculas e sem acento, com o mesmo tamanho do original (os trechos de evidência saem dele)."""
    return "".join(unicodedata.normalize("NFD", c)[0].lower()[0] for c in texto)


def _singular(palavra):
    return palavra[:-1] if palavra.endswith("s") else palavra


def _tokens(norm):
    """(palavra, posição inicial, posição final) de cada palavra do texto sem acento."""
    return [(m.group(), m.start(), m.end()) for m in re.finditer(r"[a-z]+", norm)]


def _pessoas(norm):
    """[(palavra de pessoa sem plural, início, fim)] só das que têm contexto de pessoa (ver DETERMINANTES)."""
    tokens, aceitas, validas = _tokens(norm), set(), []
    for k, (raw, i, j) in enumerate(tokens):
        palavra = _singular(raw)
        if palavra not in PESSOAS or norm[i - 1:i] == "-" or norm[j:j + 1] == "-":  # "arta-preta": composto
            continue
        antes = range(max(0, k - 2), k)
        numeral = re.search(r"\d\s*$", norm[:i])
        if (k == 0 or numeral or any(_e_determinante(tokens[a][0]) or a in aceitas for a in antes)
                or CONTEXTO_DEPOIS.search(norm[j:j + 45])):
            aceitas.add(k)
            validas.append((palavra, i, j))
    return validas


def _e_determinante(raw):
    return raw in DETERMINANTES or (len(raw) == 4 and distancia(raw, "huma") <= 1)  # "hnma" do OCR


def _palavras(norm):
    """(palavra sem plural, posição inicial, posição final) de cada palavra do texto sem acento."""
    return [(_singular(raw), i, j) for raw, i, j in _tokens(norm)]


def _sem_repetir(itens):
    return list(dict.fromkeys(itens))


# --- classificação ---

def _titulo_de_fuga(titulo):
    """Título "PRETO FUGIDO" ou a seção "ESCRAVOS FUGIDOS" (com erros de OCR)."""
    if not titulo:
        return False
    return "fugid" in _simples(titulo) or e_secao(titulo, secoes=TITULOS_FUGA)


def _tem_palavra_de_fuga(norm):
    for palavra, _, _ in _palavras(norm):
        if palavra in PALAVRAS_FUGA or any(len(palavra) >= 10 and distancia(palavra, f) <= 2 for f in FUGA_FUZZY):
            return True
    return False


def _verbo(abertura, norm):
    """"fuga", "venda", "compra", "aluguel", "precisa" ou None: pela abertura; sem ela, pelo verbo mais cedo."""
    if abertura in ABERTURA_TIPO:
        return ABERTURA_TIPO[abertura]
    achados = [(m.start(), tipo) for padrao, tipo in VERBOS if (m := re.search(padrao, norm))]
    return min(achados)[1] if achados else None


def _fugio_mal_lido(norm):
    """A 1ª palavra depois da numeração de um aviso é "fugio"/"fugiu" com erro de OCR ("24. Fabio no dia...").

    Aceita até 2 erros se a palavra tem 5 letras e termina em "io"/"iu" (Fabio, fugio); só vale sem verbo de negócio.
    """
    tokens = _tokens(norm)
    if not tokens or len(tokens[0][0]) != 5:
        return False
    palavra = tokens[0][0]
    return any(distancia(palavra, f) <= (2 if palavra[3:] in ("io", "iu") else 1) for f in ("fugio", "fugiu"))


def _achar_com_premio(norm):
    """"quem o achar ... gratificado" falando de gente (palavra de pessoa mesmo sem contexto): fuga sem a palavra fugio."""
    return bool(ACHAR.search(norm) and RECOMPENSA.search(norm) and any(_singular(r) in PESSOAS for r, _, _ in _tokens(norm)))


def _tipo_do_negocio(verbo, norm):
    """(tipo, procura) de venda/compra/aluguel; "precisa" olha se pede alugar ou comprar."""
    if verbo != "precisa":
        return verbo, verbo == "compra"  # COMPRA-SE: quem anuncia quer obter alguém
    pedido = PEDIDO.search(norm)
    # PRECISA-SE + pessoa sem dizer alugar/comprar: quase sempre é emprego (aluguel de serviço); é só heurística
    return ("compra" if pedido and pedido.group(1).startswith("compr") else "aluguel"), True


def classificar(anuncio):
    """(tipo, procura) do anúncio.

    Precedência: 1. título/seção de fuga; 2. abertura de fuga; 3. sem verbo de negócio: movimento de porto
    ("equip. 6 ... carga") é outro; 4. sem verbo de negócio: palavras de fuga no texto, ou "quem achar ... gratificado"
    com gente (para "VENDE-SE ... não fugio" não virar fuga; aviso numerado "N." precisa delas); 5. fala de pessoa
    (palavra de pessoa com contexto de pessoa; "seda preta" não vale); 6. ama de leite (vale mesmo com
    ALUGA-SE/VENDE-SE); 7. venda/compra/aluguel; 8. outro. `procura` é o lado da demanda (quem anuncia quer obter alguém): True para COMPRA-SE e PRECISA-SE
    (alugar, comprar ou só pessoa); False para VENDE-SE, ALUGA-SE e OFFERECE-SE.
    """
    texto = anuncio.get("texto") or ""
    norm = _simples(texto)
    abertura = anuncio.get("abertura") or achar_abertura(texto) or achar_numeracao(texto)
    verbo = _verbo(abertura, norm)
    if _titulo_de_fuga(anuncio.get("titulo")) or verbo == "fuga":
        return "fuga", False
    if verbo is None and NAVIO.search(norm):
        return "outro", False
    if verbo is None and (_tem_palavra_de_fuga(norm) or _achar_com_premio(norm)
                          or (abertura == "N." and _fugio_mal_lido(norm))):
        return "fuga", False
    if not (_pessoas(norm) or SRA.search(norm)):
        return "outro", False
    if verbo is None:  # abertura "N." ou nenhuma: o verbo pode estar no meio do texto
        verbo = _verbo(None, norm)
    procura = verbo in ("precisa", "compra")
    if LEITE.search(norm):
        return "ama_de_leite", procura
    if verbo is None:
        return "outro", False
    return _tipo_do_negocio(verbo, norm)


# --- extração ---

def _sexo(pessoas):
    """('m' | 'f' | 'ambos' | None, palavras que o justificaram) pelas pessoas anunciadas (ver `_pessoas`).

    "Sra", "homem", "senhor", nomes de quem anuncia e ofícios não decidem; "ambos" só com pessoas dos dois sexos.
    """
    masculino = next((p for p, _, _ in pessoas if PESSOAS[p] == "m"), None)
    feminino = next((p for p, _, _ in pessoas if PESSOAS[p] == "f"), None)
    if masculino and feminino:
        return "ambos", f"{masculino}, {feminino}"
    return ("m", masculino) if masculino else ("f", feminino) if feminino else (None, None)


def _intervalo(m):
    """(min, max) do que `IDADE`/`IDADE_OUTRO` achou, ou None se fora de 0-90."""
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    a, b = min(a, b), max(a, b)
    return (a, b) if b <= IDADE_MAXIMA else None


def _idade(texto, norm):
    """(min, max, trecho) ou (None, None, None); descarta tempo decorrido ("ha 2 para 3 annos")."""
    intervalos, trechos = [], []
    fim = 0
    for m in IDADE_TANTOS.finditer(norm):
        a = int(m.group(1))
        if a <= IDADE_MAXIMA:
            intervalos.append((a, a + 9))
            trechos.append(texto[m.start():m.end()])
            fim = max(fim, m.end())
    for m in IDADE.finditer(norm):
        if TEMPO_ANTES.search(norm[max(0, m.start() - 20):m.start()]):
            continue
        intervalo = _intervalo(m)
        if intervalo:
            intervalos.append(intervalo)
            trechos.append(texto[m.start():m.end()])
            fim = max(fim, m.end())
    if not intervalos:
        return None, None, None
    for m in IDADE_OUTRO.finditer(norm, fim):
        intervalo = _intervalo(m)
        if intervalo:
            intervalos.append(intervalo)
            trechos.append(texto[m.start():m.end()])
    return min(a for a, _ in intervalos), max(b for _, b in intervalos), " | ".join(trechos)


def _nacao(palavra, original):
    """A nação que a palavra (sem acento) é, ou None; com 1 erro de OCR só se tiver inicial maiúscula."""
    maiuscula = original[:1].isupper()
    if palavra in NAO_NACOES or (palavra in NACAO_AMBIGUAS and not maiuscula):
        return None
    if palavra in NACAO_FORMAS:
        return NACAO_FORMAS[palavra]
    if not maiuscula or len(palavra) < NACAO_LETRAS_MINIMAS - 1:
        return None
    d, forma = min((distancia(palavra, f), f) for f in NACAO_FORMAS if len(f) >= NACAO_LETRAS_MINIMAS)
    return NACAO_FORMAS[forma] if d <= NACAO_ERROS else None


def _nacoes(texto, norm):
    """([nações padronizadas], [palavras do texto que as justificaram])."""
    achadas = []
    tokens = _tokens(norm)
    for k, (raw, i, j) in enumerate(tokens):
        palavra = _singular(raw)
        anterior = tokens[k - 1][0] if k else ""
        if palavra in NACAO_AMBIGUAS and not (anterior.startswith("na") or anterior in ("de", "da")):
            continue  # "Mina" sozinha pode ser tudo; vale depois de "nação"/"naçio" ou "de"
        nome = _nacao(palavra, texto[i:j])
        if nome:
            achadas.append((nome, texto[i:j]))
    return _sem_repetir(n for n, _ in achadas), _sem_repetir(t for _, t in achadas)


def _cores(texto, norm):
    de_pessoa = {i for _, i, _ in _pessoas(norm)}
    achadas = [(CORES[p], texto[i:j]) for p, i, j in _palavras(norm)
               if p in CORES and (p in COR_LIVRE or p not in PESSOAS or i in de_pessoa)]
    return _sem_repetir(c for c, _ in achadas), _sem_repetir(t for _, t in achadas)


def _condicao(texto, norm):
    """('escravizado' | 'forro' | 'livre' | None, trecho). Forro vence escravo, que vence livre."""
    for padrao, valor in ((FORRO, "forro"), (ESCRAVIZADO, "escravizado"), (LIVRE, "livre")):
        m = padrao.search(norm)
        if m:
            return valor, texto[m.start():m.end()]
    return None, None


def _nomes(texto):
    nomes = []
    for m in NOME.finditer(texto):
        palavras = m.group(1).split()
        if _simples(palavras[0]) in NAO_NOMES:
            continue
        if len(palavras) > 1 and _simples(palavras[1]) in NAO_NOMES:
            palavras = palavras[:1]
        nomes.append(" ".join(palavras))
    return _sem_repetir(nomes)


def _oficios(texto, norm):
    achados = []
    for padrao, padrao_forma in OFICIOS:
        for m in re.finditer(rf"\b{padrao}\b", norm):
            achados.append((m.start(), padrao_forma or _singular(m.group())))
    for m in OFFICIAL_DE.finditer(norm):
        if m.group(1) not in NAO_OFICIOS:
            achados.append((m.start(), _singular(m.group(1))))
    return _sem_repetir(forma for _, forma in sorted(achados))


def extrair(texto):
    """Dict com sexo, idade_min/idade_max, nacoes, cores, condicao, nomes, oficios, recompensa, valor, endereco e
    `evidencias` (campo -> trecho que o justificou). Nunca lança erro: texto vazio ou None dá campos vazios."""
    texto = texto or ""
    norm = _simples(texto)
    evidencias = {}

    sexo, ev = _sexo(_pessoas(norm))
    if ev:
        evidencias["sexo"] = ev
    idade_min, idade_max, ev = _idade(texto, norm)
    if ev:
        evidencias["idade"] = ev
    nacoes, ev = _nacoes(texto, norm)
    if nacoes:
        evidencias["nacoes"] = ", ".join(ev)
    cores, ev = _cores(texto, norm)
    if cores:
        evidencias["cores"] = ", ".join(ev)
    condicao, ev = _condicao(texto, norm)
    if ev:
        evidencias["condicao"] = ev
    nomes = _nomes(texto)
    if nomes:
        evidencias["nomes"] = ", ".join(nomes)
    oficios = _oficios(texto, norm)
    if oficios:
        evidencias["oficios"] = ", ".join(oficios)
    m = RECOMPENSA.search(norm)
    if m:
        evidencias["recompensa"] = texto[m.start():m.end()]
    m = VALOR.search(norm)
    valor = texto[m.start(1):m.end(1)] if m else None
    if valor:
        evidencias["valor"] = valor
    m = ENDERECO.search(norm)
    endereco = texto[m.start():m.end()] if m else None
    if endereco:
        evidencias["endereco"] = endereco

    return {
        "sexo": sexo, "idade_min": idade_min, "idade_max": idade_max, "nacoes": nacoes, "cores": cores,
        "condicao": condicao, "nomes": nomes, "oficios": oficios, "recompensa": bool(evidencias.get("recompensa")),
        "valor": valor, "endereco": endereco, "evidencias": evidencias,
    }


def extrair_anuncio(anuncio):
    """`classificar` e `extrair` num dict só (tipo, procura, campos..., versao)."""
    tipo, procura = classificar(anuncio)
    return {"tipo": tipo, "procura": procura, **extrair(anuncio.get("texto")), "versao": VERSAO_CAMPOS}


# --- orquestração: lê os anúncios do banco, extrai e grava ---

CAMPOS_DA_TABELA = ("tipo", "procura", "sexo", "idade_min", "idade_max", "nacoes", "cores", "condicao", "nomes",
                    "oficios", "recompensa", "valor", "endereco", "evidencias")


def linha_do_banco(anuncio_id, campos):
    """Dict de `extrair_anuncio` na forma de uma linha de `anuncio_campos` (listas e evidências como JSON)."""
    linha = {k: campos[k] for k in CAMPOS_DA_TABELA}
    for k in ("nacoes", "cores", "nomes", "oficios"):
        linha[k] = list(linha[k] or [])
    linha["evidencias"] = dict(linha["evidencias"] or {})
    return {"anuncio_id": anuncio_id, **linha}


def resumir(linhas):
    """Contagens das linhas extraídas: total, por tipo e sexo, com idade, nações mais comuns, nomes, recompensa."""
    return {
        "total": len(linhas),
        "por_tipo": dict(Counter(l["tipo"] for l in linhas)),
        "por_sexo": dict(Counter(l["sexo"] or "sem" for l in linhas)),
        "com_idade": sum(l["idade_min"] is not None for l in linhas),
        "nacoes": Counter(n for l in linhas for n in l["nacoes"]).most_common(10),
        "com_nome": sum(bool(l["nomes"]) for l in linhas),
        "com_recompensa": sum(bool(l["recompensa"]) for l in linhas),
    }


def formatar_resumo(r):
    """O resumo de `resumir` em texto para o terminal."""
    def contagens(d):
        return ", ".join(f"{k}: {n}" for k, n in sorted(d.items(), key=lambda kn: -kn[1])) or "nenhum"
    nacoes = ", ".join(f"{n} ({q})" for n, q in r["nacoes"]) or "nenhuma"
    return "\n".join([
        f"{r['total']} anúncios processados",
        f"Por tipo: {contagens(r['por_tipo'])}", f"Por sexo: {contagens(r['por_sexo'])}",
        f"Com idade: {r['com_idade']}", f"Nações mais comuns: {nacoes}",
        f"Com nome: {r['com_nome']}", f"Com recompensa: {r['com_recompensa']}"])


def processar(banco, versao_anuncios, versao=VERSAO_CAMPOS, limite=None, lote=LOTE_CAMPOS):
    """Extrai os campos dos anúncios da versão e grava em lotes (regravar a mesma `versao` substitui). Devolve o resumo."""
    anuncios = banco.anuncios_para_campos(versao_anuncios)[:limite]
    linhas = [linha_do_banco(a["id"], extrair_anuncio(a)) for a in anuncios]
    for i in range(0, len(linhas), lote):
        banco.registrar_campos(versao, linhas[i:i + lote])
    return resumir(linhas)
