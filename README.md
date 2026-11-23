# Projeto: anúncios de escravizados na Hemeroteca Digital Brasileira

Contexto e objetivos: [projeto.md](projeto.md). Notas da reunião: [contexto.md](contexto.md).
**O que vamos buscar** (a amostra do grupo) e quantas páginas há para cada termo: [termos_busca.md](termos_busca.md). Script da amostra: `scripts/amostra.py`.
Quer só ajudar a capturar? [tutorial_captura.md](tutorial_captura.md).
O que já foi feito e o que falta: [planejamento.md](planejamento.md). Como usar a ferramenta: [guia_ferramenta.md](guia_ferramenta.md). Explicação passo a passo, com exemplo de 10 anúncios: [notebooks/como_funciona.ipynb](notebooks/como_funciona.ipynb).
Como funciona a parte de linguagem natural (limpeza do texto e modelagem de tópicos): [linguagem_natural.md](linguagem_natural.md).

## Trabalhar no repositório (para o grupo)

**Primeira vez:**

```bash
git clone https://github.com/DiegoSamim/projetoDadosCompSoc.git
cd projetoDadosCompSoc
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
sudo apt install tesseract-ocr tesseract-ocr-por
```

- O arquivo **`.env`**, com a chave do banco, **não está no repositório**. Peça à Pessoa 1 por um canal privado e coloque na raiz do projeto.
- Confira com `PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao --pessoa N`, em que N é o seu número no [planejamento](planejamento.md).

**A cada dia de trabalho:**

```bash
git pull                                   # pega o que os outros subiram
# ... trabalhe ...
git add <arquivos que você mudou>
git commit -m "o que você fez, em uma frase"
git push
```

**Regras:**

- **Nunca** suba o `.env` nem a pasta `data/`. O `.gitignore` já bloqueia os dois. Não use `git add -f`.
- Os **dados** (páginas, textos, anúncios) vão para o **banco**, não para o git. O git guarda código e documentos.
- Antes de subir mudança no código, rode os testes: `.venv/bin/python -m pytest -q`.
- Se o `git push` recusar porque alguém subiu antes, rode `git pull` e depois `git push` de novo.

## Estado atual

| Etapa | Módulo | Situação |
| --- | --- | --- |
| 1. busca (metadados e links das ocorrências) | `src/hdb/busca.py` | pronta, grava no banco, com retomada e testes |
| 2. captura (imagem da página) | `src/hdb/captura.py` | funciona contra o site, com uma pessoa resolvendo o CAPTCHA; fila de páginas no banco |
| 3. OCR | `src/hdb/ocr.py` | implementada (Tesseract, em tons de cinza, com escada de resolução); falta medir em volume |
| banco | `db/schema.sql`, `src/hdb/banco.py` | aplicado no Supabase (9 tabelas, as views `textos_atuais`, `panorama` e `anuncios_completos` e as funções) |
| 4. segmentação em anúncios | `src/hdb/layout.py`, `src/hdb/anuncios.py`, `hdb anuncios` | heurística pronta, com testes; a qualidade só se confirma olhando as páginas |
| panorama de acervos | `src/hdb/acervos.py`, `hdb acervos`, `hdb panorama` | pronto; panorama do RJ 1850–1859 completo (186 periódicos) |
| campos dos anúncios | `src/hdb/campos.py`, `hdb campos` | pronto (versão `c2`, heurística); falta conferir amostra |
| relatório metodológico | `src/hdb/relatorio.py`, `hdb relatorio` | pronto |
| amostra do grupo | `scripts/amostra.py` | plano decidido (69 páginas, 5 tipos × 4 períodos); falta listar e capturar |
| 5. corpus padronizado | `hdb corpus` (a fazer) | não iniciada; plano em [linguagem_natural.md](linguagem_natural.md) |
| 6. modelagem de tópicos | `hdb topicos` (a fazer) | não iniciada; plano em [linguagem_natural.md](linguagem_natural.md) |
| avaliação do OCR | `src/hdb/avaliacao.py` | opcional (exige transcrição à mão) |

Testes (sem rede, sem navegador e sem Supabase): `python -m pytest`.

## Banco e captura

Fluxo: `buscar` registra no banco as páginas com o termo; `capturar` reserva páginas pendentes,
baixa a imagem, faz o OCR e grava o texto. A imagem é apagada depois de gravada (ou copiada com
`--guardar-imagens`). Quem captura é registrado, e duas pessoas nunca recebem a mesma página.

Pré-requisitos (uma vez por máquina):

1. **Supabase.** O `.mcp.json` aponta para o projeto; para o schema ser aplicado pelo MCP, rodar
   `/mcp`, autenticar `supabase` e reiniciar a sessão. O schema está em `db/schema.sql`.
2. **Tesseract**, com o idioma português: pacotes `tesseract-ocr` e `tesseract-ocr-por`
   (por exemplo, `sudo apt install tesseract-ocr tesseract-ocr-por`).
3. **Arquivo `.env`** na raiz, com a chave secreta do projeto (não é compartilhado nem versionado):

   ```
   SUPABASE_URL=https://<projeto>.supabase.co
   SUPABASE_SECRET_KEY=<chave secreta>
   ```

Comandos (a partir da raiz, com `PYTHONPATH=src`):

```
python -m hdb buscar --bib 364568_04 --termo fugido --limite 150
python -m hdb capturar --bib 364568_04 --max-paginas 100
python -m hdb capturar --modo janela --workers 2 --guardar-imagens ~/imagens
python -m hdb importar
python -m hdb reprocessar --limite 20
python -m hdb anuncios --limite 5 --depurar data/depuracao
python -m hdb status
```

- `buscar`: grava acervo, páginas (pendentes) e ocorrências. Se a coleta cair, repetir o comando
  continua de onde parou.
- `capturar`: opções `--quem` (padrão: usuário do sistema), `--bib`, `--termo`, `--max-paginas`
  (padrão 50), `--aleatorio`, `--modo terminal|janela`, `--workers` (OCR em paralelo, padrão 4),
  `--guardar-imagens DIR`. Páginas com erro voltam à fila até 3 tentativas. Com Ctrl+C, as páginas
  reservadas e não concluídas voltam para a fila. Imagens que sobraram em `data/tmp/` de uma
  execução interrompida são lidas antes de capturar páginas novas.
- `importar`: carrega os CSVs de `data/ocorrencias/` e faz o OCR das imagens já baixadas em
  `data/imagens/`, marcando-as como `ok`, sem recapturar.
- `reprocessar`: refaz o OCR das imagens que já estão no disco (sem rede, sem CAPTCHA) e grava a
  nova leitura. Opções: `--pasta` (uma ou mais, com `<bib>/<bib>_<página>.jpg`; padrão `data/amostra`,
  `data/falhas_ocr` e `data/imagens`), `--quem`, `--workers` (padrão 4), `--limite`. Para cada página
  imprime a comparação com a leitura mais recente (confiança, caracteres e fração de palavras
  plausíveis, isto é, só letras e ao menos 3 caracteres) e, no fim, quantas melhoraram, pioraram e
  foram recuperadas (estavam em erro), com a confiança média antes e depois. Texto com menos de
  200 caracteres não é gravado. Uma página em erro vira `ok`; uma já `ok` só ganha a leitura nova.
  As imagens não são apagadas nem movidas.
- `anuncios`: separa em colunas e anúncios as páginas já lidas (veja a seção abaixo).
- `status`: páginas por status, por acervo e por termo, últimos erros e páginas por CAPTCHA.

Modos de OCR (`config.OCR_MODO`):

- `pagina` (padrão): o Tesseract lê a página inteira (reduzida, em tons de cinza) com `--psm 3` e decide o
  layout. O texto sai com uma quebra entre linhas e duas entre blocos ou parágrafos, e `colunas`
  guarda o número de blocos.
- `colunas`: `detectar_colunas` separa as colunas e cada uma é lida com `--psm 4`. Corta ao meio
  os blocos de largura total (como os avisos).

O OCR lê em **tons de cinza**, sem binarizar (`config.OCR_BINARIZAR = False`): a binarização (Otsu)
apagava páginas inteiras. A leitura usa uma escada de resolução (`config.OCR_LARGURAS`): reduz a
3000 px e, se o texto tiver menos de 200 caracteres, tenta 4500 px; se nenhuma chegar lá, vale a
leitura com mais caracteres.

A coluna `motor` de `textos_ocr` identifica a variante (ex.: `tesseract-5.3.4 por psm3-pagina-cinza`;
`...-cinza-4500` se a 2ª largura foi a escolhida; `-otsu` no lugar de `-cinza` com binarização), então
`textos_ocr` pode ter **mais de uma leitura por página**. A view `textos_atuais` devolve, por página,
a leitura mais recente (`criado_em`); é o "texto atual".

Quando o OCR falha (texto com menos de 200 caracteres ou erro), a página fica com status `erro` e
**não é recapturada**: a imagem vai para `data/falhas_ocr/<bib>/`, para inspeção ou novo OCR local.
Só falhas de captura voltam para a fila (até 3 tentativas). A reserva é feita em lotes de 10 páginas.

Dois modos para resolver o CAPTCHA, sempre digitado por uma pessoa:

- `terminal` (padrão, navegador invisível): a imagem do código é salva em `data/captura/captcha.png`
  e o terminal pede o código; Enter vazio troca a imagem.
- `janela`: o navegador fica visível, o terminal avisa com um sinal sonoro e a captura continua
  quando o CAPTCHA é resolvido na janela.

## Panorama de acervos

Descobre quais periódicos a HDB tem num estado e década e em quantas páginas de cada um um termo aparece.
Exige a migração `panorama_acervos` (fim de `db/schema.sql`).

```
hdb acervos --local RJ --periodo "1850 - 1859" [--sonda janeiro --sonda rio] [--limite 10] [--modo janela]
hdb panorama --local RJ --periodo "1850 - 1859" --termo '"escravo fugido"' [--termo T2] [--recontar] [--ordenar percentual]
```

- `acervos` abre a tela de busca (aba Locality), percorre a lista de periódicos por posição e grava o código
  (`bib`) e os anos de cada um. É retomável; se a tela pedir CAPTCHA, para (a ferramenta não o resolve).
- `panorama` conta, por requisições simples, as páginas com cada termo em cada acervo, completa o total de
  páginas e imprime o ranking. A HDB conta o acervo inteiro, não só a década: acervos que começam antes ou
  terminam depois dela saem com o aviso "cobre mais que a década".
- `hdb importar` também carrega `data/contagens_termos.csv` e `data/paginas_por_acervo.csv`.

## Colunas e anúncios

O Tesseract (psm 3) devolve a página como um bloco em que linhas de colunas vizinhas se misturam
(nas páginas de 6 a 8 colunas a "linha" mediana cruza ~60% da largura). `hdb.layout` desfaz isso a
partir das palavras com posição: corta cada linha do Tesseract nos espaços de 35 px ou mais (ou
depois do fio vertical `|`), acha a borda esquerda de cada coluna (o `x0` mais comum entre os
segmentos largos, descartando bordas com pouco apoio em relação às demais) e ordena os segmentos
coluna a coluna, de cima para baixo. Segmentos que cruzam colunas (títulos, avisos) ficam marcados
como `largo`. `hdb.anuncios` separa cada coluna em anúncios: um novo começa num título (letra
grande ou caixa alta curta), numa palavra de abertura (`VENDE-SE`, `FUGIO`... com 1 erro de OCR
tolerado), num espaço vertical grande ou depois de uma linha curta que acaba em ponto. Também
descarta cabeçalho, rodapé e lixo do OCR do `texto` (o `texto_bruto` guarda tudo) e junta palavras
partidas pelo hífen de fim de linha. Para páginas de letra grande (Diário do RJ de 1821, onde o espaço normal entre palavras já passa de
50 px), o espaço de corte e as tolerâncias em px se ajustam à página (mediana do espaço entre
palavras e altura mediana da letra). Avisos numerados ("34. Fugio...") e títulos de seção conhecidos
("ESCRAVOS FUGIDOS") também abrem anúncio. Os limiares estão em `config.py`. A versão padrão da
segmentação é `v2`.

```
python -m hdb anuncios --pasta data/amostra --versao v2 --limite 10 --depurar data/depuracao
python -m hdb anuncios --palavras tests/fixtures/palavras_p320.json --imagem data/falhas_ocr/364568_04/364568_04_00320.jpg --depurar data/depuracao
```

- Para cada imagem (mesma descoberta de `reprocessar`) imprime nº de colunas, segmentos, anúncios,
  anúncios com abertura reconhecida e com título. Opções: `--pasta`, `--versao` (padrão `v2`; regravar a
  mesma versão substitui os anúncios dela), `--limite`, `--sem-banco`, `--quem`.
- **Cache de palavras:** o OCR com posição é gravado em `data/ocr_palavras/<bib>/<bib>_<pagfis>.json`
  e, se o arquivo existir, o OCR não é refeito (apague-o para reler). `--palavras ARQUIVO.json
  [--imagem IMG.jpg]` roda sobre um desses JSON, sem OCR nem banco.
- **`--depurar DIR`:** um PNG por página (900 px de largura) com as bordas das colunas em vermelho e
  cada anúncio como retângulo colorido com seu número, para revisar a olho.
- **Tabela `anuncios`** (`db/schema.sql`, função `registrar_anuncios`): por página e versão, `ordem`,
  `coluna`, `titulo`, `abertura`, `texto_bruto`, `texto`, `confianca`, caixa (`x0,y0,x1,y1`, em px da
  imagem lida pelo OCR, 3000 px de largura), `n_linhas`, `largo` e `busca` (tsvector). Já aplicada no Supabase.
- **A segmentação é heurística.** Não há rótulos manuais para medi-la: nas páginas densas
  (classificados de 1850) ela mistura ou parte anúncios com frequência, e o texto de áreas com
  ornamentos ou borrões sai ruim. A qualidade só se confirma olhando as páginas (PNG de depuração).

## Campos dos anúncios

`hdb campos [--versao-anuncios v2] [--versao c1] [--limite N]` (`hdb.campos`) lê os anúncios de uma
versão da segmentação, classifica cada um (`fuga`, `venda`, `compra`, `aluguel`, `ama_de_leite`,
`outro`; `procura` é True quando quem anuncia quer obter alguém: COMPRA-SE e PRECISA-SE) e extrai
sexo, idade, nações, cores, condição, nomes, ofícios, recompensa, valor e endereço, com o trecho que
justificou cada campo (`evidencias`). Grava na tabela `anuncio_campos` (por anúncio e versão; regravar a
mesma versão substitui) e imprime um resumo. A view `anuncios_completos` junta anúncio, página, acervo e
campos, com o `periodo_legal` pelo ano. É heurístico (OCR de grafia antiga): confira por amostragem.

## Relatório metodológico

`hdb relatorio [--saida ARQUIVO.md]` gera, só a partir do banco, um Markdown que diz como a coleta foi feita:
regras da busca, termos e acervos, capturas, OCR, anúncios e campos, panorama, limites conhecidos e créditos.
Sem `--saida`, grava em `relatorios/relatorio_<AAAA-MM-DD>.md`.

## CAPTCHA da HDB

Desde 03/10/2025 a HDB pede um CAPTCHA para carregar as imagens das páginas. A busca por metadados
(etapa 1) não é afetada. Esta ferramenta **não resolve CAPTCHAs automaticamente**: a captura deve
pausar e esperar uma pessoa digitar o código.

## Créditos

**pyHDB.** O panorama de acervos e o relatório metodológico vêm das ideias do pyHDB, de Eric Brasil
(licença MIT):

> BRASIL, Eric. pyHDB – Ferramenta Heurística para a Hemeroteca Digital Brasileira. *História da
> Historiografia*, v. 15, n. 40, p. 186–217, 2022. DOI 10.15848/hh.v15i40.1904.
> https://github.com/ericbrasiln/pyHDB

- **O que veio dela:** o panorama de acervos (quais periódicos existem por local e década, e quantas páginas
  de cada um trazem um termo) e o relatório que explica o método usado na coleta.
- **O que fizemos diferente:** o CAPTCHA é sempre resolvido por uma pessoa (a ferramenta não o contorna);
  o navegador não se disfarça; os dados ficam num banco compartilhado (Supabase), e não em arquivos soltos;
  o OCR é feito aqui, localmente (Tesseract).

**Extração de campos.** A ideia de tirar sexo, idade, nação, nome e outros dados dos anúncios é inspirada em
https://github.com/luizhenriquesoares/hemeroteca-digital. Nenhum código dele foi reaproveitado.

**Comandos novos:** `acervos`, `panorama`, `campos` e `relatorio` (veja as seções acima e o
[guia](guia_ferramenta.md)).
