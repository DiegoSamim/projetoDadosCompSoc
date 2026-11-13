"""Configurações compartilhadas por todos os módulos."""
from pathlib import Path

BASE_URL = "https://memoria.bn.gov.br/docreader/"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)

# Pausa entre requisições à BN, em segundos. Não reduzir: o acervo está sendo reaberto aos poucos.
PAUSA = 1.5
TIMEOUT = 60
TENTATIVAS = 4  # tentativas por requisição, com espera crescente (2 s, 4 s, 8 s...)

RAIZ = Path(__file__).resolve().parents[2]
DATA_DIR = RAIZ / "data"
OCORRENCIAS_DIR = DATA_DIR / "ocorrencias"
IMAGENS_DIR = DATA_DIR / "imagens"
CAPTURA_DIR = DATA_DIR / "captura"  # perfil do navegador e imagem do CAPTCHA
TMP_DIR = DATA_DIR / "tmp"  # imagens esperando o OCR; apagadas depois de gravar no banco
FALHAS_OCR_DIR = DATA_DIR / "falhas_ocr"  # imagens cujo OCR falhou, para inspeção ou novo OCR local
OCR_PALAVRAS_DIR = DATA_DIR / "ocr_palavras"  # cache das palavras do OCR, <bib>/<bib>_<pagfis>.json
DEPURACAO_DIR = DATA_DIR / "depuracao"  # PNGs de `hdb anuncios --depurar`
AMOSTRA_DIR = DATA_DIR / "amostra"
PASTAS_REPROCESSAR = (AMOSTRA_DIR, FALHAS_OCR_DIR, IMAGENS_DIR)  # onde `reprocessar` procura imagens

# Captura das imagens (etapa 2). A pausa é fixa: a ferramenta não disfarça o ritmo.
PAUSA_CAPTURA = 3  # segundos entre páginas
TAMANHO_HIRES = "6464x8940"
TIMEOUT_IMAGEM = 60  # segundos esperando a imagem da página aparecer
MAX_PAGINAS = 50  # páginas por execução
TIMEOUT_CAPTCHA_JANELA = 600  # segundos que a pessoa tem para resolver o CAPTCHA no modo janela

# OCR (Tesseract) e fila de páginas no banco
OCR_LARGURAS = (3000, 4500)  # larguras, em px, tentadas em ordem; a 2ª só entra se a 1ª render pouco texto
OCR_BINARIZAR = False  # a binarização (Otsu) apagava páginas inteiras; em tons de cinza o Tesseract lê melhor
OCR_MIN_CARACTERES = 200  # abaixo disso o OCR conta como falha
OCR_MODO = "pagina"  # "pagina" (psm 3, layout pelo Tesseract) ou "colunas" (detectar_colunas + psm 4)
OCR_WORKERS = 4  # processos de OCR em paralelo; mais que isso arrisca a memória
LOTE_RESERVA = 10  # páginas reservadas por vez, para a reserva não expirar no meio da execução
RESERVA_MINUTOS = 30  # depois disso uma página reservada volta para a fila
MAX_TENTATIVAS = 3  # tentativas por página antes de desistir

# Marcos legais usados para dividir o corpus (ano de início da década -> período)
PERIODOS_LEGAIS = (
    (1850, "1831–1850 (Feijó → Eusébio)"),
    (1870, "1850–1871 (Eusébio → Ventre Livre)"),
    (9999, "1871–1888 (Ventre Livre → Áurea)"),
)

# Layout por colunas (hdb.layout), em px da imagem lida pelo OCR (3000 px de largura)
# Em páginas de letra grande (Diário do RJ de 1821: letra de ~75 px) o espaço normal entre palavras já é
# ~52 px, então limites fixos em px cortariam toda linha. O espaço de corte vira max(LAYOUT_GAP, LAYOUT_GAP_REL x
# a mediana do espaço entre palavras da página) e as tolerâncias em px (TOL_BORDA, LARGURA_BORDA, CRUZA) crescem
# com a escala da letra: altura mediana das palavras / LAYOUT_LETRA_REF (>= 1).
LAYOUT_GAP = 35  # espaço mínimo entre palavras vizinhas a partir do qual a linha do Tesseract é cortada (normal: 5-15 px)
LAYOUT_GAP_REL = 3.5  # vezes o espaço mediano entre palavras da página
LAYOUT_LETRA_REF = 15  # altura de letra (px) em que as tolerâncias em px valem como estão
LAYOUT_LARGURA_BORDA = 150  # (x escala) só segmentos assim de largos votam nas bordas das colunas (descarta fragmentos)
LAYOUT_TOL_BORDA = 30  # (x escala) x0 de segmentos a até isso um do outro votam na mesma borda (recuo de parágrafo, ruído)
LAYOUT_APOIO_MIN = 10  # votos mínimos para uma borda poder ser chamada de "forte"
LAYOUT_APOIO_REL = 0.35  # fração da mediana de apoio das bordas fortes que uma borda precisa ter; as espúrias
# (apoio 16-17 contra 70-130 das reais) cortariam colunas ao meio, e um limite absoluto não pega páginas diferentes
LAYOUT_CRUZA = 30  # (x escala) px: palavra que começa antes de (borda - isto) e acaba depois de (borda + isto) cruza a fronteira
LAYOUT_LARGO = 1.5  # segmento com largura >= isto x a coluna típica cruza colunas (título, aviso)

# Separação de anúncios (hdb.anuncios)
ANUNCIO_TITULO_ALTURA = 1.4  # altura >= isto x a mediana da coluna: letra de título
ANUNCIO_TITULO_MAIUSCULAS = 0.7  # fração das letras em maiúscula de um título só em caixa alta
ANUNCIO_TITULO_LETRAS = 0.6  # fração mínima de letras de um título (barra sujeira em letras grandes)
ANUNCIO_TITULO_CONFIANCA = 70  # confiança mínima de um título: letra grande de verdade é lida bem; ruído e ornamentos, não
ANUNCIO_TITULO_PALAVRAS = 8  # máximo de palavras de um título em caixa alta
ANUNCIO_ESPACO_VERTICAL = 1.6  # espaço entre linhas > isto x o passo normal de linha: anúncio novo
ANUNCIO_LINHA_CURTA = 0.75  # linha que acaba em ponto com menos que esta fração da largura da coluna fecha o anúncio
ANUNCIO_FRAGMENTO = 25  # anúncio sem título e sem abertura com menos caracteres é anexado ao anterior
ANUNCIO_ABERTURAS = (
    "PRECISA-SE", "VENDE-SE", "VENDEM-SE", "ALUGA-SE", "ALUGAM-SE", "COMPRA-SE", "COMPRAM-SE",
    "FUGIO", "FUGIU", "EVADIO-SE", "DESAPPARECEU", "GRATIFICA-SE", "PERDEU-SE", "ROUBARAM",
    "ACHA-SE", "OFFERECE-SE", "ENDE-SE",  # ENDE-SE: erro comum de OCR para VENDE-SE
)
ANUNCIO_SECOES = ("ESCRAVOS FUGIDOS", "ANNUNCIOS", "AVISOS", "NOTICIAS MARITIMAS")  # títulos de seção dos jornais
ANUNCIO_SECAO_ERROS = 2  # distância de edição tolerada (ignora espaços, pontuação e maiúsculas: "E S C R A V O S")
ANUNCIO_ABERTURA_ERROS = 1  # distância de edição tolerada na 1ª palavra (ignora hífen e maiúsculas)
LIXO_CONFIANCA = 25  # segmento com confiança média menor que isto é lixo do OCR (exceto título)
LIXO_LETRAS = 0.4  # segmento com menos letras que esta fração dos caracteres é lixo (exceto título)
CABECALHO = 0.025  # fração do topo da página onde número ou caixa alta é cabeçalho
RODAPE = 0.03  # idem, na base
VERSAO_CAMPOS = "c2"  # versão da extração de campos (hdb.campos); muda quando as heurísticas mudam
LOTE_CAMPOS = 500  # campos gravados por chamada ao banco
VERSAO_ANUNCIOS = "v2"  # versão da segmentação em anúncios; muda quando as heurísticas mudam
DEPURACAO_LARGURA = 900  # px de largura dos PNGs de depuração

# Panorama de acervos (hdb.acervos): lista de periódicos da tela de busca e contagem por termo
HDB_URL = "https://memoria.bn.gov.br/hdb/"
# Termos usados para abrir o leitor de um periódico e ler o código (bib). Têm de ser frequentes e fora da lista
# de palavras ignoradas da HDB (`de` devolve 0 resultados); a 2ª e a 3ª só entram se a anterior não abrir o leitor.
PANORAMA_SONDAS = ("janeiro", "rio", "anno")
TIMEOUT_JANELA_BUSCA = 20  # segundos esperando a janela do leitor abrir (periódico sem a sonda pode não abrir)
ESPERA_POSTBACK = 3  # segundos depois de escolher estado, período ou periódico (a tela recarrega por postback)
CONTAGENS_CSV = DATA_DIR / "contagens_termos.csv"  # categoria,termo,bib,acervo,paginas,coletado_em
PAGINAS_CSV = DATA_DIR / "paginas_por_acervo.csv"  # bib,acervo,paginas
