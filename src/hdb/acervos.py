"""Panorama de acervos: quais periódicos a HDB tem num estado e década, e em quantas páginas cada um tem um termo.

A descoberta usa o navegador (a lista de periódicos só existe na tela de busca) e nunca resolve CAPTCHA:
se ele aparecer, a execução para. As contagens usam só `requests`. O Playwright é importado dentro das
funções de navegador, para os testes não dependerem dele.
"""
import csv
import re
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from hdb import busca, config
from hdb.busca import _requisitar, nova_sessao

IFRAME_CAPTCHA = 'iframe[name="CaptchaWnd"]'
ABA_LOCALIDADE = 2  # índice em `#RadTabStrip1 li`: Newspaper, Period, Locality
PADRAO_BIB = re.compile(r"[0-9A-Za-z]+(?:_[0-9A-Za-z]+)*")  # descarta "[cache]" das buscas em "Todos"


# ---------- partes puras ----------

def bib_do_endereco(url):
    """Código do acervo (`bib`) de um endereço do leitor; None se não há ou não parece um código."""
    valores = {k.lower(): v for k, v in parse_qs(urlparse(url or "").query).items()}.get("bib")
    return valores[0] if valores and PADRAO_BIB.fullmatch(valores[0]) else None


def anos_do_acervo(descricao):
    """(ano_inicio, ano_fim) de "Jornal do Commercio (RJ) - 1850 a 1859"; (None, None) se não houver anos."""
    m = re.search(r"(\d{4})\s*a\s*(\d{4})\s*$", descricao or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"-\s*(\d{4})\s*$", descricao or "")
    return (int(m.group(1)),) * 2 if m else (None, None)


# ---------- páginas de um acervo (usado também por scripts/contar_paginas.py) ----------

def pagina_aberta(sessao, bib, pagfis):
    """Página que o leitor realmente abre ao pedir `pagfis` (None se não vier)."""
    r = _requisitar(sessao, "GET", f"{config.BASE_URL}docreader.aspx?bib={bib}&pagfis={pagfis}")
    campo = BeautifulSoup(r.text, "lxml").find(id="hPagFis")
    return int(campo.get("value")) if campo is not None and campo.get("value") else None


def existe(sessao, bib, pagfis):
    """A página `pagfis` existe? Fora do acervo o leitor abre a primeira página, não a pedida."""
    return pagina_aberta(sessao, bib, pagfis) == pagfis


def total_de_paginas(sessao, bib):
    """Páginas do acervo: da primeira à última válida (a numeração nem sempre começa em 1).

    A primeira é a que o leitor abre ao pedir a página 1. A última sai de uma busca binária,
    depois de dobrar o passo até falhar.
    """
    inicio = pagina_aberta(sessao, bib, 1)
    baixo, passo = inicio, 1000
    while existe(sessao, bib, baixo + passo):
        baixo, passo = baixo + passo, passo * 2
    alto = baixo + passo
    while alto - baixo > 1:
        meio = (baixo + alto) // 2
        if existe(sessao, bib, meio):
            baixo = meio
        else:
            alto = meio
    return baixo - inicio + 1


# ---------- camada do navegador ----------

class NavegadorHDB:
    """A tela de busca da HDB (aba Locality) conduzida pelo Playwright; `page` e `context` já abertos."""

    def __init__(self, page, context):
        self.page, self.context = page, context

    def _esperar_postback(self):
        self.page.wait_for_timeout(config.ESPERA_POSTBACK * 1000)

    def _escolher(self, abrir, itens, escolher):
        """Abre a lista em `abrir` e clica no item de `itens` que `escolher` aponta (por texto ou posição)."""
        self.page.click(abrir)
        lista = self.page.locator(itens)
        lista.first.wait_for(state="attached")
        textos = [t.strip() for t in lista.all_text_contents()]
        alvo = escolher(textos)
        if alvo is None:
            raise LookupError(f"item não encontrado em {itens}")
        lista.nth(alvo).click()
        self._esperar_postback()
        return textos

    def preparar(self, local, periodo):
        """Abre a tela, escolhe estado e período e devolve os nomes da lista de periódicos (o 1º é "Todos")."""
        self.page.goto(config.HDB_URL)
        self.page.locator("#RadTabStrip1 li").nth(ABA_LOCALIDADE).click()
        self._esperar_postback()
        self._escolher("#UFCmb3_Arrow", "#UFCmb3_DropDown li",
                       lambda t: t.index(local) if local in t else None)
        self._escolher("#PeriodoCmb3_Input", "#PeriodoCmb3_DropDown li",
                       lambda t: next((i for i, x in enumerate(t) if periodo in x), None))
        self.page.click("#PeriodicoCmb3_Arrow")
        textos = [t.strip() for t in self.page.locator("#PeriodicoCmb3_DropDown li").all_text_contents()]
        self.page.click("#PeriodicoCmb3_Arrow")  # fecha; `consultar` abre de novo
        return textos

    def captcha(self):
        """Há um CAPTCHA visível na tela de busca?"""
        return self.page.locator(IFRAME_CAPTCHA).first.is_visible()

    def consultar(self, posicao, termo):
        """Busca `termo` no periódico da `posicao` da lista. Devolve (endereço, descrição) da janela, ou None."""
        from playwright.sync_api import TimeoutError as TimeoutPlaywright

        self._escolher("#PeriodicoCmb3_Arrow", "#PeriodicoCmb3_DropDown li", lambda t: posicao)
        self.page.fill("#PesquisaTxt3", termo)
        try:
            with self.context.expect_page(timeout=config.TIMEOUT_JANELA_BUSCA * 1000) as info:
                self.page.click("#PesquisarBtn3")
        except TimeoutPlaywright:
            return None
        janela = info.value
        try:
            janela.wait_for_load_state("domcontentloaded", timeout=config.TIMEOUT_JANELA_BUSCA * 1000)
            try:
                descricao = janela.locator("#AcervoDescLbl").text_content(timeout=5000)
            except TimeoutPlaywright:
                descricao = None
            return janela.url, (descricao or "").strip() or None
        finally:
            janela.close()


@contextmanager
def _navegador_real(visivel):
    """Abre o Chromium e entrega um `NavegadorHDB`; fecha ao sair."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not visivel)
        try:
            context = browser.new_context()
            yield NavegadorHDB(context.new_page(), context)
        finally:
            browser.close()


# ---------- descoberta ----------

def _sondar(navegador, posicao, sondas):
    """Tenta cada sonda até o leitor abrir com um bib. Devolve (bib, descrição, None) ou (None, None, erro)."""
    motivos = []
    for sonda in sondas:
        try:
            resultado = navegador.consultar(posicao, sonda)
        except Exception as e:  # um periódico problemático não derruba a descoberta dos outros
            motivos.append(f"{sonda}: {type(e).__name__}: {e}".splitlines()[0])
            continue
        if resultado is None:
            motivos.append(f"{sonda}: sem janela")
            continue
        url, descricao = resultado
        bib = bib_do_endereco(url)
        if bib:
            return bib, descricao, None
        motivos.append(f"{sonda}: janela sem bib")
    return None, None, "; ".join(motivos) or "sem sondas"


def _gravar_descoberta(banco, local, periodo, posicao, nome_lista, bib, descricao, erro):
    if bib:
        inicio, fim = anos_do_acervo(descricao)
        banco.garantir_acervo(bib, descricao or nome_lista)
        banco.atualizar_acervo(bib, nome=descricao, ano_inicio=inicio, ano_fim=fim)
    banco.registrar_acervo_periodo(local, periodo, posicao, nome_lista, bib=bib, erro=erro)


def _a_descobrir(nomes, gravadas):
    """Posições (>= 1) ainda sem bib, ou cujo nome na lista mudou desde a gravação."""
    for posicao, nome in enumerate(nomes):
        g = gravadas.get(posicao)
        if posicao >= 1 and not (g and g["bib"] and g["nome_lista"] == nome):
            yield posicao, nome


def descobrir_acervos(banco, local, periodo, sondas=config.PANORAMA_SONDAS, limite=None, visivel=False,
                      navegador=None):
    """Grava no banco o bib de cada periódico de (local, período); retomável por posição.

    `limite` é o máximo de periódicos consultados nesta execução. `navegador` é para os testes.
    Devolve quantos foram descobertos com bib.
    """
    with _navegador_real(visivel) if navegador is None else _sem_abrir(navegador) as nav:
        nomes = nav.preparar(local, periodo)
        print(f"{len(nomes) - 1} periódicos em {local}, {periodo}.")
        gravadas = {r["posicao"]: r for r in banco.acervos_do_periodo(local, periodo)}
        feitos = achados = 0
        for posicao, nome in _a_descobrir(nomes, gravadas):
            if limite is not None and feitos >= limite:
                break
            if nav.captcha():
                print("A tela de busca pediu CAPTCHA. A ferramenta não o resolve: pare aqui, espere a HDB "
                      "liberar e rode de novo (as posições já gravadas são puladas).")
                break
            bib, descricao, erro = _sondar(nav, posicao, sondas)
            _gravar_descoberta(banco, local, periodo, posicao, nome, bib, descricao, erro)
            feitos += 1
            achados += bool(bib)
            print(f"{posicao:3} {nome[:50]:50} {bib or 'ERRO: ' + erro}")
            time.sleep(config.PAUSA_CAPTURA)
    print(f"{achados} de {feitos} periódicos consultados com bib.")
    return achados


@contextmanager
def _sem_abrir(navegador):
    yield navegador


# ---------- contagens ----------

def contar_panorama(banco, local, periodo, termos, recontar=False, sessao=None, com_total=True):
    """Conta, em cada acervo de (local, período), as páginas com cada termo; completa o total de páginas.

    Só faz a requisição do que falta (`recontar` refaz as contagens). Cada resultado é gravado na hora.
    O total de páginas custa ~20 requisições, então só é calculado nos acervos em que algum termo apareceu
    (o percentual só interessa neles); `com_total=False` o dispensa.
    """
    sessao = sessao or nova_sessao()
    bibs = list(dict.fromkeys(r["bib"] for r in banco.acervos_do_periodo(local, periodo) if r["bib"]))
    for bib in bibs:
        try:
            for termo in termos:
                if recontar or banco.contagem(bib, termo) is None:
                    n = busca.total_ocorrencias(sessao, bib, termo)
                    banco.registrar_contagem(bib, termo, n)
                    print(f"{bib} {termo}: {n}")
            tem_termo = any((banco.contagem(bib, t) or 0) > 0 for t in termos)
            if com_total and tem_termo and (banco.acervo(bib) or {}).get("total_paginas") is None:
                total = total_de_paginas(sessao, bib)
                banco.atualizar_acervo(bib, total_paginas=total)
                print(f"{bib}: {total} páginas")
        except requests.RequestException as e:
            print(f"{bib}: erro de rede ({e}); siga com outra execução")


def ranking(banco, local, periodo, termo, ordenar="paginas"):
    """Linhas do ranking do termo: dicts em ordem decrescente de `ordenar` ("paginas" ou "percentual")."""
    linhas = banco.panorama(local, periodo, termo)
    if ordenar not in ("paginas", "percentual"):
        raise ValueError(f"ordenar deve ser 'paginas' ou 'percentual', não {ordenar!r}")

    def chave(r):
        return (r[ordenar] is not None, r[ordenar] or 0, r["paginas"])

    saida = []
    for r in sorted(linhas, key=chave, reverse=True):
        anos = f"{r['ano_inicio']}-{r['ano_fim']}" if r["ano_inicio"] else "?"
        saida.append({**r, "anos": anos,
                      "aviso": "cobre mais que a década" if r["cobre_mais_que_a_decada"] else ""})
    return saida


def formatar_ranking(linhas):
    """O ranking de `ranking` como tabela de texto."""
    cabeca = f"{'pos':>3}  {'periódico':36} {'bib':10} {'anos':10} {'páginas':>8} {'total':>8} {'%':>7}  aviso"
    texto = [cabeca]
    for r in linhas:
        total = r["total_paginas"] if r["total_paginas"] is not None else "?"
        pct = f"{r['percentual'] * 100:.2f}" if r["percentual"] is not None else "?"
        nome = (r["nome_lista"] or r["nome"] or "")[:36]
        texto.append(f"{r['posicao']:>3}  {nome:36} {r['bib']:10} {r['anos']:10} {r['paginas']:>8} "
                     f"{total:>8} {pct:>7}  {r['aviso']}")
    return "\n".join(texto)


# ---------- importação dos CSVs de data/ ----------

def _ler_csv(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        return []
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def importar_contagens(banco):
    """Carrega `config.CONTAGENS_CSV` em `contagens`; mantém o nome de acervo que já existir."""
    linhas = _ler_csv(config.CONTAGENS_CSV)
    for linha in linhas:
        banco.garantir_acervo(linha["bib"], linha.get("acervo"))
        banco.registrar_contagem(linha["bib"], linha["termo"], int(linha["paginas"]),
                                 contado_em=linha.get("coletado_em") or None)
    if linhas:
        print(f"{config.CONTAGENS_CSV.name}: {len(linhas)} contagens")


def importar_paginas_por_acervo(banco):
    """Carrega `config.PAGINAS_CSV` em `acervos.total_paginas`."""
    linhas = _ler_csv(config.PAGINAS_CSV)
    for linha in linhas:
        banco.garantir_acervo(linha["bib"], linha.get("acervo"))
        banco.atualizar_acervo(linha["bib"], total_paginas=int(linha["paginas"]))
    if linhas:
        print(f"{config.PAGINAS_CSV.name}: {len(linhas)} acervos")
