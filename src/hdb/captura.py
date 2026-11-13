"""Captura das imagens das páginas (etapa 2): navegador produz, processos de OCR consomem.

A HDB exige CAPTCHA para mostrar imagens. Quem resolve é sempre uma pessoa: este módulo só
mostra o CAPTCHA e espera o código; todo o resto (navegar, baixar, ler o texto, gravar no banco)
é automático. A imagem fica em data/tmp/ só até o texto ir para o banco.
O Playwright é importado dentro das funções de navegador, para os testes não dependerem dele.
"""
import json
import re
import shutil
import signal
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from itertools import chain
from io import BytesIO
from pathlib import Path

from hdb import acervos, anuncios, config, layout, ocr
from hdb.armazenamento import ler_csv_parcial

IFRAME_CAPTCHA = 'iframe[name="CaptchaWnd"]'


# ---------- partes puras ----------

def caminho_tmp(bib, pagfis):
    """Onde a imagem de uma página espera o OCR."""
    return config.TMP_DIR / f"{bib}_{int(pagfis):05d}.jpg"


def pagina_do_tmp(caminho):
    """(bib, página física) de um arquivo de data/tmp/; o bib pode ter "_" (ex.: 364568_04_00040.jpg)."""
    bib, pagfis = Path(caminho).stem.rsplit("_", 1)
    return bib, int(pagfis)


def _tamanho_da_imagem(caminho):
    from PIL import Image

    with Image.open(caminho) as im:
        return im.size


def _mover_para(caminho, pasta):
    """Move a imagem para `pasta/<bib>/`."""
    destino = Path(pasta) / pagina_do_tmp(caminho)[0] / Path(caminho).name
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(caminho, destino)


def _guardar_ou_apagar(caminho, guardar):
    """Depois de gravar no banco: move a imagem para `guardar/<bib>/` ou a apaga."""
    if guardar:
        _mover_para(caminho, guardar)
    else:
        Path(caminho).unlink(missing_ok=True)


def _paginas_reservadas(banco, quem, max_paginas, tentadas, **filtros):
    """Páginas reservadas em lotes de `LOTE_RESERVA`, até `max_paginas` ou acabar a fila.

    Os ids vão para `tentadas`, que o banco exclui do lote seguinte (página que falhou
    nesta execução não volta). Reservar aos poucos evita a reserva expirar no fim de uma execução longa.
    """
    while len(tentadas) < max_paginas:
        lote = banco.reservar(quem, min(config.LOTE_RESERVA, max_paginas - len(tentadas)),
                              excluir=tentadas, **filtros)
        if not lote:
            return
        for pagina in lote:
            tentadas.append(pagina["id"])
            yield pagina


# ---------- partes de navegador ----------

def captcha_visivel(page):
    """Há um CAPTCHA na tela?"""
    return page.locator(IFRAME_CAPTCHA).first.is_visible()


def fechar_aviso(page):
    """Fecha o aviso de pesquisa de opinião, se aparecer."""
    aviso = page.locator("#RadWindowWrapper_PesqOpniaoRadWindow")
    try:
        aviso.wait_for(state="visible", timeout=3000)
    except Exception:
        return
    try:  # com o CAPTCHA por cima, o clique não passa; o aviso fica e não atrapalha
        aviso.locator("a.rwCloseButton").first.click(timeout=3000)
    except Exception:
        pass


def _salvar_imagem_captcha(frame):
    config.CAPTURA_DIR.mkdir(parents=True, exist_ok=True)
    destino = config.CAPTURA_DIR / "captcha.png"
    frame.locator("#RadCaptcha1_CaptchaImageUP").screenshot(path=str(destino))
    return destino


def _resolver_no_terminal(page):
    frame = page.frame(name="CaptchaWnd")
    destino = _salvar_imagem_captcha(frame)
    while captcha_visivel(page):
        print(f"\nCAPTCHA: abra {destino.as_uri()} e digite o código (Enter vazio troca o código).")
        codigo = input("Código: ").strip()  # EOFError sobe para `capturar`, que encerra
        if not codigo:
            frame.locator("#RadCaptcha1_CaptchaLinkButton").click()
            page.wait_for_timeout(1500)
            destino = _salvar_imagem_captcha(frame)
            continue
        frame.locator("#RadCaptcha1_CaptchaTextBox").fill(codigo)
        frame.locator("#EnviarBtn_input").click()
        page.wait_for_timeout(2000)
        if captcha_visivel(page):
            print("Código incorreto.")
            destino = _salvar_imagem_captcha(frame)


def _resolver_na_janela(page):
    print("\a\nCAPTCHA: resolva na janela do navegador (a captura continua sozinha depois).", flush=True)
    page.locator(IFRAME_CAPTCHA).first.wait_for(state="hidden", timeout=config.TIMEOUT_CAPTCHA_JANELA * 1000)


def resolver_com_pessoa(page, modo):
    """Espera uma pessoa resolver o CAPTCHA visível: `modo` é "terminal" ou "janela"."""
    if modo == "terminal":
        _resolver_no_terminal(page)
    else:
        _resolver_na_janela(page)


def _src_imagem(page):
    return page.evaluate("document.getElementById('DocumentoImg')?.src || ''")


def carregar_pagina(page, pagfis, tamanho):
    """Pede a imagem da página `pagfis` no tamanho dado, pela função da própria página."""
    page.evaluate(
        "([tamanho, pf]) => { document.getElementById('HiddenSize').value = tamanho; PagCarrega(pf); }",
        [tamanho, int(pagfis)],
    )


def esperar_imagem(page, anterior, modo, timeout=None):
    """Espera um src novo com "cache" em #DocumentoImg. Devolve (src, captchas resolvidos)."""
    timeout = timeout or config.TIMEOUT_IMAGEM
    captchas = 0
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if captcha_visivel(page):
            resolver_com_pessoa(page, modo)
            captchas += 1
            limite = time.monotonic() + timeout  # o tempo da pessoa não conta
            continue
        src = _src_imagem(page)
        if "cache" in src and src != anterior:
            return src, captchas
        page.wait_for_timeout(500)
    raise TimeoutError(f"a imagem não apareceu em {timeout} s")


def baixar_imagem(context, src, destino):
    """Baixa `src` com a sessão do navegador e grava em `destino`. Devolve (largura, altura, bytes)."""
    from PIL import Image

    resp = context.request.get(src, timeout=config.TIMEOUT_IMAGEM * 1000)
    tipo = resp.headers.get("content-type", "")
    if not resp.ok or not tipo.startswith("image/"):
        raise RuntimeError(f"resposta inesperada ao baixar a imagem: {resp.status} {tipo}")
    corpo = resp.body()
    largura, altura = Image.open(BytesIO(corpo)).size
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(corpo)
    return largura, altura, len(corpo)


def _capturar_pagina(page, context, pagina, modo, tamanho, abrir):
    """Captura uma página para data/tmp/. Devolve (CAPTCHAs resolvidos, largura, altura, bytes)."""
    bib, pagfis = pagina["bib"], pagina["pagina_fisica"]
    captchas = 0
    if abrir:
        page.goto(f"{config.BASE_URL}docreader.aspx?bib={bib}&pagfis={pagfis}")
        fechar_aviso(page)
        # A página abre carregando sozinha a imagem em baixa resolução. Esperamos por ela antes
        # de pedir a alta; senão a baixa pode chegar depois e ser tomada pela alta.
        _, captchas = esperar_imagem(page, "", modo)
    anterior = _src_imagem(page)
    for tentativa in (1, 2):
        carregar_pagina(page, pagfis, tamanho)
        try:
            src, n = esperar_imagem(page, anterior, modo)
            captchas += n
            break
        except TimeoutError:
            if tentativa == 2:
                raise
    atual = page.evaluate("document.getElementById('hPagFis')?.value")
    if str(atual) != str(pagfis):
        raise RuntimeError(f"a página carregada é a {atual}, não a {pagfis}")
    largura, altura, nbytes = baixar_imagem(context, src, caminho_tmp(bib, pagfis))
    return captchas, largura, altura, nbytes


# ---------- OCR e banco ----------

def _ignorar_sigint():
    """Nos processos de OCR: o Ctrl+C é tratado só pelo programa principal, que espera os OCRs em andamento."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _criar_executor(workers):
    """Processos de OCR; função à parte para os testes trocarem por threads."""
    return ProcessPoolExecutor(max_workers=workers, initializer=_ignorar_sigint)


def _enviar_ocr(executor, pendentes, pagina, caminho, largura, altura, nbytes, segundos, captchas):
    """Põe a imagem na fila do OCR; `pendentes` guarda o que falta para gravar o resultado."""
    futuro = executor.submit(ocr.extrair_texto, str(caminho))
    pendentes[futuro] = {"pagina": pagina, "caminho": caminho, "largura": largura, "altura": altura,
                         "bytes": nbytes, "segundos": segundos, "captchas": captchas}


def _gravar_resultado(banco, quem, futuro, info, guardar, apagar):
    """Grava no banco o resultado do OCR. Devolve "ok", "erro", ou None se o banco falhou."""
    pagina, caminho = info["pagina"], info["caminho"]
    try:
        resultado = futuro.result()
        erro = None
        if len(resultado["texto"]) < config.OCR_MIN_CARACTERES:
            erro = f"texto com {len(resultado['texto'])} caracteres (mínimo {config.OCR_MIN_CARACTERES})"
    except Exception as e:
        erro = f"{type(e).__name__}: {e}".splitlines()[0]
    segundos = info["segundos"] + (0 if erro else resultado["segundos"])
    try:
        if erro:
            banco.registrar_erro(pagina["id"], quem, "ocr", erro, segundos, info["captchas"])
        else:
            banco.registrar_sucesso(pagina["id"], quem, info["largura"], info["altura"], info["bytes"],
                                    resultado, segundos, info["captchas"])
    except Exception as e:  # o banco caiu: a imagem fica em data/tmp/ e é reaproveitada na próxima execução
        print(f"{pagina['bib']} p.{pagina['pagina_fisica']}: falha ao gravar no banco ({e}); imagem mantida")
        return None
    if apagar and erro:
        _mover_para(caminho, config.FALHAS_OCR_DIR)  # não é recapturada: fica para inspeção ou novo OCR local
    elif apagar:
        _guardar_ou_apagar(caminho, guardar)
    status = "erro" if erro else "ok"
    print(f"{pagina['bib']} p.{pagina['pagina_fisica']}: {status}" + (f" ({erro})" if erro else ""))
    return status


def _gravar_prontos(banco, quem, pendentes, contagem, guardar, apagar=True, esperar=False):
    """Grava os OCRs terminados; com `esperar`, aguarda todos. Atualiza `contagem`."""
    while pendentes:
        prontos = [f for f in pendentes if f.done()]
        if not prontos and esperar:
            prontos = wait(pendentes, return_when=FIRST_COMPLETED).done
        if not prontos:
            return
        for futuro in prontos:
            status = _gravar_resultado(banco, quem, futuro, pendentes.pop(futuro), guardar, apagar)
            if status:
                contagem[status] += 1


def _processar_orfas(banco, quem, executor, pendentes):
    """Envia ao OCR as imagens de data/tmp/ que ficaram de execuções interrompidas."""
    for caminho in sorted(config.TMP_DIR.glob("*.jpg")):
        bib, pagfis = pagina_do_tmp(caminho)
        pagina = banco.pagina(bib, pagfis)
        if pagina is None:
            print(f"{caminho.name}: página desconhecida no banco; imagem mantida")
        elif pagina["status"] == "ok":
            caminho.unlink()  # já foi gravada: só sobrou o arquivo
        else:
            print(f"{bib} p.{pagfis}: reaproveitando a imagem de uma execução interrompida")
            largura, altura = _tamanho_da_imagem(caminho)
            _enviar_ocr(executor, pendentes, pagina, caminho, largura, altura,
                        caminho.stat().st_size, 0, 0)


def _resumo(contagem, captchas):
    por_captcha = f"{contagem['ok'] / captchas:.1f}" if captchas else "sem CAPTCHA"
    print(f"\nResumo: {contagem['ok']} ok, {contagem['erro']} erros, "
          f"{captchas} CAPTCHAs resolvidos (páginas por CAPTCHA: {por_captcha}).")


def capturar(banco, quem, bib=None, termo=None, max_paginas=config.MAX_PAGINAS, aleatorio=False,
             modo="terminal", tamanho=config.TAMANHO_HIRES, workers=config.OCR_WORKERS, guardar=None):
    """Reserva páginas do banco (até `max_paginas`, em lotes), captura (uma pessoa resolve o CAPTCHA) e faz o OCR."""
    from playwright.sync_api import sync_playwright

    contagem = {"ok": 0, "erro": 0}
    total_captchas = 0
    bib_aberto = None
    pendentes = {}
    config.TMP_DIR.mkdir(parents=True, exist_ok=True)
    executor = _criar_executor(workers)
    try:
        _processar_orfas(banco, quem, executor, pendentes)
        # Termina as órfãs antes de reservar: senão a mesma página (ainda pendente) seria capturada de novo.
        _gravar_prontos(banco, quem, pendentes, contagem, guardar, esperar=True)
        fila = _paginas_reservadas(banco, quem, max_paginas, [], bib=bib, termo=termo, aleatorio=aleatorio)
        primeira = next(fila, None)
        if primeira is None:
            print("Nenhuma página disponível para capturar.")
            _resumo(contagem, 0)
            return
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                config.CAPTURA_DIR / "perfil", headless=(modo == "terminal"))
            page = context.pages[0] if context.pages else context.new_page()
            try:
                for pagina in chain([primeira], fila):
                    pagfis = pagina["pagina_fisica"]
                    inicio = time.monotonic()
                    try:
                        captchas, largura, altura, nbytes = _capturar_pagina(
                            page, context, pagina, modo, tamanho, pagina["bib"] != bib_aberto)
                        bib_aberto = pagina["bib"]
                    except EOFError:
                        print("\nEntrada encerrada durante o CAPTCHA; captura interrompida.")
                        break  # a página volta para a fila em liberar_reservas, sem gastar tentativa
                    except Exception as e:
                        erro = f"{type(e).__name__}: {e}".splitlines()[0]
                        bib_aberto = None  # força um goto novo na próxima página
                        banco.registrar_erro(pagina["id"], quem, "captura", erro, time.monotonic() - inicio, 0)
                        contagem["erro"] += 1
                        print(f"{pagina['bib']} p.{pagfis}: erro ({erro})")
                    else:
                        total_captchas += captchas
                        _enviar_ocr(executor, pendentes, pagina, caminho_tmp(pagina["bib"], pagfis),
                                    largura, altura, nbytes, time.monotonic() - inicio, captchas)
                    _gravar_prontos(banco, quem, pendentes, contagem, guardar)
                    time.sleep(config.PAUSA_CAPTURA)
            finally:
                context.close()
        _gravar_prontos(banco, quem, pendentes, contagem, guardar, esperar=True)
        _resumo(contagem, total_captchas)
    except KeyboardInterrupt:
        print("\nInterrompido; as páginas não concluídas voltam para a fila.")
        for futuro in pendentes:
            futuro.cancel()
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
        liberadas = banco.liberar_reservas(quem)
        if liberadas:
            print(f"{liberadas} páginas devolvidas à fila.")


def importar_existentes(banco, quem, workers=config.OCR_WORKERS):
    """Carrega no banco os CSVs de data/ocorrencias/, as contagens e páginas por acervo, e faz o OCR de data/imagens/.

    As imagens ficam onde estão. Páginas que já estão ok no banco não são lidas de novo.
    """
    for csv in sorted(config.OCORRENCIAS_DIR.glob("*.csv")):
        linhas = ler_csv_parcial(csv)
        for linha in linhas:
            banco.registrar_ocorrencia(linha)
        print(f"{csv.name}: {len(linhas)} ocorrências")
    acervos.importar_contagens(banco)
    acervos.importar_paginas_por_acervo(banco)

    contagem = {"ok": 0, "erro": 0}
    pendentes = {}
    with _criar_executor(workers) as executor:
        for jpg in sorted(config.IMAGENS_DIR.glob("*/*.jpg")):
            meta_json = jpg.with_suffix(".json")
            if not meta_json.exists():
                print(f"{jpg.name}: sem .json; ignorada")
                continue
            meta = json.loads(meta_json.read_text(encoding="utf-8"))
            pagina = banco.garantir_pagina(meta)
            if pagina["status"] == "ok":
                continue
            _enviar_ocr(executor, pendentes, pagina, jpg, meta["largura"], meta["altura"],
                        meta["bytes"], 0, 0)
        _gravar_prontos(banco, quem, pendentes, contagem, None, apagar=False, esperar=True)
    print(f"Imagens importadas: {contagem['ok']} ok, {contagem['erro']} erros.")


# ---------- reprocessamento ----------

PALAVRA = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")  # só letras (com acento), hífen só no meio


def fracao_palavras_plausiveis(texto):
    """Fração dos tokens com só letras e ao menos 3 caracteres (pontuação nas pontas é ignorada)."""
    tokens = [t.strip(".,;:!?()[]{}\"'«»…—–") for t in texto.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if len(t) >= 3 and PALAVRA.fullmatch(t)) / len(tokens)


def _imagens_das_pastas(pastas):
    """Imagens `<pasta>/<bib>/<bib>_<pagfis>.jpg` (ou direto na pasta), sem repetir (bib, página); vale a primeira."""
    vistas, imagens = set(), []
    for pasta in pastas:
        for caminho in sorted(chain(Path(pasta).glob("*/*.jpg"), Path(pasta).glob("*.jpg"))):
            try:
                chave = pagina_do_tmp(caminho)
            except ValueError:
                print(f"{caminho}: nome fora do padrão <bib>_<página>.jpg; ignorada")
                continue
            if chave in vistas:
                print(f"{caminho}: página repetida; ignorada")
                continue
            vistas.add(chave)
            imagens.append((chave, caminho))
    return imagens


def _medidas(texto, confianca):
    return {"conf": confianca, "caracteres": len(texto), "plausiveis": fracao_palavras_plausiveis(texto)}


def _anterior(banco, pagina):
    """Medidas da leitura mais recente da página, ou None se não há."""
    textos = banco.textos(pagina["id"])
    if not textos:
        return None
    t = max(textos, key=lambda t: t["criado_em"])
    return _medidas(t["texto"], t["confianca"] or 0.0)


def _linha_comparacao(nome, antes, depois):
    if antes is None:
        return (f"{nome}: conf {depois['conf']:.1f} | caracteres {depois['caracteres']} | "
                f"palavras plausíveis {depois['plausiveis']:.0%} (sem leitura anterior)")
    return (f"{nome}: conf {antes['conf']:.1f} -> {depois['conf']:.1f} | "
            f"caracteres {antes['caracteres']} -> {depois['caracteres']} | "
            f"palavras plausíveis {antes['plausiveis']:.0%} -> {depois['plausiveis']:.0%}")


def _gravar_reprocesso(banco, quem, info, futuro, contagem):
    """Compara com a leitura anterior e grava o novo texto; texto curto ou erro não grava."""
    pagina = info["pagina"]
    nome = f"{pagina['bib']} p.{pagina['pagina_fisica']}"
    try:
        resultado = futuro.result()
    except Exception as e:
        print(f"{nome}: erro ({type(e).__name__}: {str(e).splitlines()[0]})")
        contagem["erros"] += 1
        return
    if len(resultado["texto"]) < config.OCR_MIN_CARACTERES:
        print(f"{nome}: erro (texto com {len(resultado['texto'])} caracteres "
              f"(mínimo {config.OCR_MIN_CARACTERES})); não gravado")
        contagem["erros"] += 1
        return
    antes = _anterior(banco, pagina)
    depois = _medidas(resultado["texto"], resultado["confianca"])
    print(_linha_comparacao(nome, antes, depois))
    banco.registrar_reprocesso(pagina["id"], quem, info["largura"], info["altura"], info["bytes"], resultado)
    contagem["gravadas"] += 1
    if pagina["status"] != "ok":
        contagem["recuperadas"] += 1
    if antes is not None:
        contagem["antes"].append(antes["conf"])
        contagem["depois"].append(depois["conf"])
        contagem["melhoraram"] += depois["conf"] > antes["conf"]
        contagem["pioraram"] += depois["conf"] < antes["conf"]


def _resumo_reprocesso(c):
    media = lambda v: f"{sum(v) / len(v):.1f}" if v else "-"
    print(f"\nResumo: {c['gravadas']} gravadas, {c['erros']} com erro; {c['melhoraram']} melhoraram em confiança, "
          f"{c['pioraram']} pioraram, {c['recuperadas']} recuperadas (estavam em erro); "
          f"confiança média {media(c['antes'])} -> {media(c['depois'])} "
          f"(em {len(c['antes'])} páginas com leitura anterior).")


def reprocessar(banco, quem, pastas, workers=config.OCR_WORKERS, limite=None):
    """Refaz o OCR das imagens de `pastas`, compara com a leitura anterior e grava a nova. Não mexe nas imagens."""
    pendentes = {}
    contagem = {"gravadas": 0, "erros": 0, "melhoraram": 0, "pioraram": 0, "recuperadas": 0,
                "antes": [], "depois": []}
    with _criar_executor(workers) as executor:
        for (bib, pagfis), caminho in _imagens_das_pastas(pastas):
            if limite is not None and len(pendentes) >= limite:
                break
            pagina = banco.pagina(bib, pagfis)
            if pagina is None:
                print(f"{caminho.name}: página desconhecida no banco; ignorada")
                continue
            largura, altura = _tamanho_da_imagem(caminho)
            pendentes[executor.submit(ocr.extrair_texto, str(caminho))] = {
                "pagina": pagina, "largura": largura, "altura": altura, "bytes": caminho.stat().st_size}
        while pendentes:
            for futuro in wait(pendentes, return_when=FIRST_COMPLETED).done:
                _gravar_reprocesso(banco, quem, pendentes.pop(futuro), futuro, contagem)
    _resumo_reprocesso(contagem)


# ---------- anúncios ----------

def caminho_palavras(bib, pagfis):
    """Onde ficam em cache as palavras do OCR de uma página."""
    return config.OCR_PALAVRAS_DIR / bib / f"{bib}_{int(pagfis):05d}.json"


def palavras_da_imagem(caminho, bib, pagfis):
    """Palavras do OCR da imagem; lê do cache em disco se existir, senão faz o OCR e grava o cache."""
    cache = caminho_palavras(bib, pagfis)
    if cache.exists():
        return json.loads(cache.read_text())
    dados = ocr.ler_palavras(str(caminho))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dados, ensure_ascii=False))
    return dados


def segmentar_pagina(dados):
    """Layout e anúncios das palavras de uma página ({largura, altura, palavras}), em um dict para a depuração."""
    segs, faixas, bordas = layout.ler_em_colunas(dados["palavras"], dados["largura"], anuncios.abertura_em_caixa_alta)
    achados, descartados = anuncios.separar(segs, dados["altura"])
    return {"segmentos": segs, "faixas": faixas, "bordas": bordas, "anuncios": achados, "descartados": descartados}


def desenhar_depuracao(caminho_imagem, dados, resultado, destino, largura=None, regiao=None):
    """PNG da página com as bordas das colunas em vermelho e cada anúncio num retângulo numerado.

    `largura` (padrão `DEPURACAO_LARGURA`) é a do PNG; `regiao` = (x0, y0, x1, y1), nas coordenadas do OCR,
    grava só esse recorte.
    """
    import cv2

    cinza = cv2.imread(str(caminho_imagem), cv2.IMREAD_GRAYSCALE)
    if cinza is None:
        raise ValueError(f"não consegui decodificar a imagem {caminho_imagem}")
    largura = largura or config.DEPURACAO_LARGURA
    escala = largura / dados["largura"]
    tamanho = (largura, round(dados["altura"] * escala))
    imagem = cv2.cvtColor(cv2.resize(cinza, tamanho, interpolation=cv2.INTER_AREA), cv2.COLOR_GRAY2BGR)
    cores = [(200, 90, 0), (0, 140, 0), (160, 0, 160), (0, 120, 220)]
    for a in resultado["anuncios"]:
        cor = cores[a["ordem"] % len(cores)]
        p0, p1 = (round(a["x0"] * escala), round(a["y0"] * escala)), (round(a["x1"] * escala), round(a["y1"] * escala))
        cv2.rectangle(imagem, p0, p1, cor, 1)
        corpo = 0.35 * max(escala / 0.3, 1)  # número maior nas imagens ampliadas
        cv2.putText(imagem, str(a["ordem"]), (p0[0] + 2, p0[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, corpo, cor, 1)
    for x in resultado["bordas"]:
        cv2.line(imagem, (round(x * escala), 0), (round(x * escala), tamanho[1]), (0, 0, 255), 1)
    if regiao:
        x0, y0, x1, y1 = (round(v * escala) for v in regiao)
        imagem = imagem[max(y0, 0):y1, max(x0, 0):x1]
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), imagem)


def _resumo_pagina(nome, r):
    achados = r["anuncios"]
    print(f"{nome}: {len(r['faixas'])} colunas, {len(r['segmentos'])} segmentos, {len(achados)} anúncios, "
          f"{sum(1 for a in achados if a['abertura'])} com abertura, {sum(1 for a in achados if a['titulo'])} com título")


def anuncios_do_arquivo(palavras, imagem, depurar=None):
    """Segmenta um JSON de palavras já pronto (sem OCR nem banco); `imagem` só serve para a depuração."""
    dados = json.loads(Path(palavras).read_text())
    r = segmentar_pagina(dados)
    _resumo_pagina(Path(palavras).stem, r)
    if depurar and imagem:
        desenhar_depuracao(imagem, dados, r, Path(depurar) / f"{Path(palavras).stem}.png")
    return r


def anuncios_das_paginas(banco, pastas, versao=config.VERSAO_ANUNCIOS, limite=None, depurar=None):
    """Para cada imagem de `pastas`: palavras (com cache), layout, anúncios; grava no banco se `banco` não é None."""
    total = 0
    for (bib, pagfis), caminho in _imagens_das_pastas(pastas):
        if limite is not None and total >= limite:
            break
        nome = f"{bib} p.{pagfis}"
        pagina = banco.pagina(bib, pagfis) if banco else None
        if banco and pagina is None:
            print(f"{nome}: página desconhecida no banco; ignorada")
            continue
        dados = palavras_da_imagem(caminho, bib, pagfis)
        r = segmentar_pagina(dados)
        if banco:
            banco.registrar_anuncios(pagina["id"], versao, r["anuncios"])
        _resumo_pagina(nome, r)
        if depurar:
            desenhar_depuracao(caminho, dados, r, Path(depurar) / f"{bib}_{int(pagfis):05d}.png")
        total += 1
    print(f"\n{total} páginas segmentadas.")
