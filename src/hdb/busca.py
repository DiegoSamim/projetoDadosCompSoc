"""Busca de termos na HDB: percorre as ocorrências de um acervo e registra os metadados.

Usa só `requests`: o DocReader é um formulário ASP.NET, e "próxima ocorrência" é um postback.
"""
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from hdb import config


def nova_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers["User-Agent"] = config.USER_AGENT
    return sessao


_dormir = time.sleep  # os testes trocam por uma função que só anota a espera
STATUS_BLOQUEIO = (429, 503)  # Too Many Requests e Service Unavailable: o site pede para esperar


class SiteIndisponivel(Exception):
    """O site respondeu 429/503 (ou não responde) mesmo depois de esperar; `depois_de` = segundos sugeridos."""

    def __init__(self, mensagem, status=None, depois_de=config.ESPERA_BLOQUEIO):
        super().__init__(mensagem)
        self.status = status
        self.depois_de = depois_de


def mensagem_bloqueio(status):
    return f"o site da BN pediu para esperar ({status}); tente de novo depois"


def _espera_do_cabecalho(valor):
    """Segundos do `Retry-After` (número ou data HTTP); None se ausente ou ilegível."""
    if not valor:
        return None
    valor = valor.strip()
    if valor.isdigit():
        return int(valor)
    try:
        data = parsedate_to_datetime(valor)
    except (TypeError, ValueError):
        return None
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return max(0, int((data - datetime.now(timezone.utc)).total_seconds()))


def _espera_bloqueio(resposta, bloqueios):
    """Espera antes de tentar de novo: o `Retry-After`, ou ESPERA_BLOQUEIO dobrando a cada bloqueio (teto: MAX)."""
    pedida = _espera_do_cabecalho(resposta.headers.get("Retry-After"))
    if pedida is None:
        pedida = config.ESPERA_BLOQUEIO * 2 ** (bloqueios - 1)
    return min(pedida, config.ESPERA_BLOQUEIO_MAX)


def _requisitar(sessao, metodo, url, **kwargs):
    """GET/POST com novas tentativas e espera crescente; respeita a pausa entre requisições.

    429 e 503 têm tratamento à parte: espera o que o site pedir (ou 60 s, 120 s...) e, se o bloqueio
    persistir por TENTATIVAS_BLOQUEIO respostas, levanta `SiteIndisponivel`. Os outros erros
    seguem com a espera de 2, 4, 8 s.
    """
    ultimo_erro = None
    erros = bloqueios = 0
    while True:
        try:
            r = sessao.request(metodo, url, timeout=config.TIMEOUT, **kwargs)
            if r.status_code in STATUS_BLOQUEIO:
                bloqueios += 1
                espera = _espera_bloqueio(r, bloqueios)
                if bloqueios >= config.TENTATIVAS_BLOQUEIO:
                    raise SiteIndisponivel(mensagem_bloqueio(r.status_code), r.status_code, espera)
                print(f"O site respondeu {r.status_code}; esperando {espera} s antes de tentar de novo.", flush=True)
                _dormir(espera)
                continue
            r.raise_for_status()
            _dormir(config.PAUSA)
            return r
        except requests.RequestException as e:
            ultimo_erro = e
            erros += 1
            _dormir(2 ** erros)
            if erros >= config.TENTATIVAS:
                raise ultimo_erro


def _campos_formulario(soup):
    """Campos do formulário ASP.NET (VIEWSTATE etc.) necessários para o postback."""
    return {
        i["name"]: i.get("value", "")
        for i in soup.select("form input")
        if i.get("name") and i.get("type") not in ("submit", "button", "image", "checkbox")
    }


def abrir_busca(sessao, bib, termo):
    """Abre o acervo `bib` já posicionado na 1ª ocorrência de `termo`. Retorna (url, soup)."""
    url = f"{config.BASE_URL}docreader.aspx?bib={bib}&Pesq={quote(termo)}"
    r = _requisitar(sessao, "GET", url)
    return url, BeautifulSoup(r.text, "lxml")


def total_do_rotulo(soup):
    """Total de ocorrências lido do rótulo `atual/total`; 0 se o acervo não tem o termo."""
    lbl = soup.find(id="OcorNroLbl")
    m = re.search(r"/\s*(\d+)", lbl.get_text()) if lbl else None
    return int(m.group(1)) if m else 0


def ler_ocorrencia(soup, bib, ocorrencia=1):
    """Extrai os metadados da ocorrência atual.

    O rótulo `atual/total` do servidor às vezes vem errado (volta para 1 no meio da navegação),
    por isso o número da ocorrência é controlado por quem chama; do rótulo usamos só o total.
    """
    def txt(i):
        el = soup.find(id=i)
        return el.get_text(strip=True) if el else None

    def val(i):
        el = soup.find(id=i)
        return el.get("value") if el else None

    pasta = soup.find(id="PastaTxt")
    pasta = pasta.get("title", "") if pasta else ""  # ex.: "Ano 1826\Edição 00007"
    ano = re.search(r"Ano (\d+)", pasta)
    edicao = re.search(r"Edição (\d+)", pasta)
    pagfis = val("hPagFis")
    return {
        "bib": bib,
        "acervo": txt("AcervoDescLbl"),
        "termo": val("PesquisarTxt"),
        "ocorrencia": ocorrencia,
        "total_ocorrencias": total_do_rotulo(soup),
        "ano": ano.group(1) if ano else None,
        "edicao": edicao.group(1) if edicao else None,
        "pagina": val("PagAtualTxt"),
        "pagina_fisica": pagfis,
        "link": f"{config.BASE_URL}{bib}/{pagfis}",
    }


def proxima_ocorrencia(sessao, url, soup):
    """Simula o clique em 'próxima ocorrência' e devolve o novo soup."""
    dados = _campos_formulario(soup)
    dados.update(__EVENTTARGET="OcorPosBtn", __EVENTARGUMENT="", HiddenSize="1280x900")
    r = _requisitar(sessao, "POST", url, data=dados, headers={"Referer": url})
    return BeautifulSoup(r.text, "lxml")


def total_ocorrencias(sessao, bib, termo):
    """Número de ocorrências do termo no acervo (0 se não houver). Uma requisição só."""
    _, soup = abrir_busca(sessao, bib, termo)
    return total_do_rotulo(soup)


def coletar_ocorrencias(sessao, bib, termo, banco, limite=None):
    """Percorre até `limite` ocorrências (todas, se None) e grava cada uma no banco.

    Devolve (ocorrências no banco, total do servidor). Se a coleta cair, uma nova chamada continua
    de onde parou, avançando as ocorrências já salvas sem registrá-las de novo. Se o site pedir para
    esperar (`SiteIndisponivel`), o que já foi gravado fica e a exceção sobe; depois de
    LISTAGEM_PASSOS_PAUSA_LONGA passos a pausa fixa entre requisições passa a PAUSA_LISTAGEM_LONGA.
    """
    passos = 0

    def avancar(soup):
        nonlocal passos
        soup = proxima_ocorrencia(sessao, url, soup)
        passos += 1
        if passos > config.LISTAGEM_PASSOS_PAUSA_LONGA:  # listagem longa: alivia o servidor (pausa fixa)
            _dormir(max(config.PAUSA_LISTAGEM_LONGA - config.PAUSA, 0))
        return soup

    url, soup = abrir_busca(sessao, bib, termo)
    total = total_do_rotulo(soup)
    if total == 0:
        return 0, 0
    alvo = min(limite, total) if limite else total

    feitas = banco.contar_ocorrencias(bib, termo)
    # O servidor guarda a posição na sessão, então reposicionar custa uma requisição por
    # ocorrência já salva (com a pausa de sempre). Não há atalho conhecido.
    for _ in range(max(feitas - 1, 0)):
        soup = avancar(soup)

    while feitas < alvo:
        if feitas:
            soup = avancar(soup)
        linha = ler_ocorrencia(soup, bib, ocorrencia=feitas + 1)
        linha["termo"] = termo  # a retomada conta por este termo; o campo da página pode vir diferente
        banco.registrar_ocorrencia(linha)
        feitas += 1
    return feitas, total


def periodo_legal(decada_inicio):
    """Período legal (marcos de 1850 e 1871) de uma década, pelo ano em que ela começa."""
    for limite, nome in config.PERIODOS_LEGAIS:
        if decada_inicio < limite:
            return nome
