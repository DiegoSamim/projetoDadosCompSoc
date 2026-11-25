# Guia da ferramenta `hdb`

Este guia explica **como a ferramenta funciona** e **como usá-la**, passo a passo. O que ainda falta construir está em [planejamento.md](planejamento.md). A parte de linguagem natural (limpeza do texto e tópicos) está em [linguagem_natural.md](linguagem_natural.md), e um exemplo com dados reais, em [notebooks/como_funciona.ipynb](notebooks/como_funciona.ipynb).

## Para que serve

A ferramenta descobre quais jornais existem, busca páginas de jornais do século XIX na Hemeroteca Digital Brasileira (HDB), lê o texto delas e separa cada página em **anúncios**. Tudo fica num banco de dados compartilhado (Supabase), para que várias pessoas trabalhem sem repetir nada.

## Como funciona

```
  Site da HDB
      │
      │ 1. buscar   ─ procura um termo num jornal e anota as páginas onde ele aparece (sem CAPTCHA)
      ▼
  Banco: páginas "pendentes"
      │
      │ 2. capturar ─ abre cada página num navegador; uma pessoa digita o CAPTCHA;
      │               baixa a imagem, lê o texto com OCR e separa os anúncios
      ▼
  Banco: texto de cada página ("ok") e palavras do OCR
      │
      │ 3. anuncios ─ descobre as colunas da página e separa os anúncios
      │               (a captura já faz isso; o comando refaz o que faltar)
      ▼
  Banco: anúncios (com título, palavra de abertura e texto limpo)
      │
      │ 4. campos   ─ tipo (fuga, venda…), sexo, idade, nação, nome, recompensa
      ▼
  Banco: anúncios com campos e período legal (view anuncios_completos)
      │
      │ 5. corpus   ─ escolhe os anúncios de pessoas escravizadas e padroniza o texto
      ▼
  Banco: corpus (texto padronizado, ao lado do original)
      │
      │ 6. topicos  ─ modelagem de tópicos (LDA); ver linguagem_natural.md
      ▼
  Banco: tópicos e a mistura de tópicos de cada anúncio → comparação entre os períodos legais
```

### As peças, uma a uma

**A busca da HDB.** A HDB diz em quais **páginas** um termo aparece, não em quais anúncios. Ela busca a **palavra exata**:

- ignora acentos e maiúsculas;
- `*` no fim pega variações (`escrav*` = escravo, escrava, escravos…);
- aspas buscam a **frase colada** (`"escravo fugido"`);
- não existe OU nem NÃO.

Quais termos usar e quantas páginas cada um tem está em [termos_busca.md](termos_busca.md).

**O CAPTCHA.** Desde 03/10/2025 a HDB pede um código de imagem para mostrar as páginas. A ferramenta **não tenta resolver o código sozinha**: ela mostra a imagem do código, uma pessoa digita, e o resto continua automaticamente. Até agora o código foi pedido uma vez a cada acervo aberto, e não a cada página.

**O OCR.** OCR (reconhecimento óptico de caracteres) é o programa que "lê" a foto da página e devolve o texto. Usamos o **Tesseract**, com o modelo de português. Ele lê a imagem em tons de cinza; se sair pouco texto, tenta de novo em resolução maior. Em jornais antigos ele erra letras ("foglo" em vez de "fogão"), principalmente nas páginas densas dos anos 1850 a 1880.

**A separação em anúncios.** O OCR devolve a página inteira, com linhas de colunas vizinhas misturadas. A ferramenta usa a **posição de cada palavra** para:
1. cortar as linhas onde há um espaço grande entre palavras (o vão entre colunas);
2. descobrir onde começa cada coluna;
3. ler coluna por coluna, de cima para baixo;
4. começar um anúncio novo quando encontra um título em letras grandes, uma palavra de abertura (`VENDE-SE`, `FUGIO`, `ALUGA-SE`, `PRECISA-SE`…), um aviso numerado ("34."), um título de seção ("ESCRAVOS FUGIDOS") ou um espaço vertical grande.

É uma regra **heurística**: funciona bem na maioria das páginas, mas pode errar. Anúncios que provavelmente misturam colunas ficam marcados como `largo`.

**O banco e o trabalho sem retrabalho.**
- Cada página tem um **status**: `pendente` (ainda não lida), `reservada` (alguém está capturando), `ok` (lida) ou `erro`.
- Quando alguém captura, o banco **reserva** um lote de páginas para essa pessoa. Duas pessoas nunca recebem a mesma página.
- Uma página `ok` nunca é capturada de novo.
- Se a captura cair, as páginas reservadas voltam para a fila (na hora, ou em 30 minutos se o programa for fechado à força).
- Falhas de captura voltam para a fila até 3 vezes. Falhas de OCR não voltam, porque capturar de novo daria o mesmo resultado; a imagem fica guardada para estudo.
- Consultas ao banco que dão timeout, erro 5xx ou 429 (muitos pedidos seguidos) são repetidas até 3 vezes, sozinhas.
- **Bloqueio do site (429 ou 503).** Quando a Biblioteca Nacional pede espera, a ferramenta espera o tempo indicado pelo site (`Retry-After`); sem essa indicação, espera 1 minuto, dobrando a cada novo bloqueio até o máximo de 15 minutos. Depois de 3 respostas de bloqueio seguidas, para e avisa "tente de novo mais tarde". Nada disso é marcado como erro de página, e o que já foi feito continua valendo.

## O que precisa estar pronto

Uma vez por computador:

| Item | Para que serve |
|---|---|
| Python com o ambiente do projeto (`.venv`) e os pacotes de `requirements.txt` | rodar a ferramenta |
| Navegador do Playwright: `.venv/bin/python -m playwright install chromium` | abrir as páginas da HDB |
| Tesseract com o idioma português (pacotes `tesseract-ocr` e `tesseract-ocr-por`) | ler o texto (OCR) |
| Arquivo `.env` na pasta do projeto, com `SUPABASE_URL` e `SUPABASE_SECRET_KEY` | acessar o banco |

O `.env` contém a **chave secreta** do banco. Não o envie em grupos de mensagem nem o publique; peça a quem administra o projeto.

Para conferir se está tudo certo:

```bash
tesseract --list-langs                      # deve listar "por"
PYTHONPATH=src .venv/bin/python -m hdb status   # deve mostrar as páginas do banco, sem erro de chave
```

## Antes de cada sessão

Abra o terminal na pasta do projeto e rode:

```bash
cd /home/diego/programacao/projetoDadosCompSoc
export PYTHONPATH=src
PY=.venv/bin/python
```

Todos os exemplos abaixo usam `$PY -m hdb ...`.

## O caminho recomendado: a amostra do grupo

Se você só quer ajudar a coletar, este é o caminho. O plano (quais termos, quais jornais, quantas páginas) já está decidido em [termos_busca.md](termos_busca.md), seção "O que vamos buscar", e guardado em `scripts/amostra.py`.

```bash
PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao --pessoa N                 # 0. ver o que falta
PYTHONPATH=src .venv/bin/python scripts/amostra.py listar --pessoa N                   # 1. listar (sem CAPTCHA, sozinho)
PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar --pessoa N --quem SeuNome  # 2. capturar (você digita o CAPTCHA; já separa os anúncios)
$PY -m hdb anuncios                                                         # 3. separar o que faltar (pula o que já está pronto)
$PY -m hdb campos                                                           # 4. extrair os campos
$PY -m hdb relatorio                                                        # 5. registrar o método
```

- **`N`** é o seu número (1, 2 ou 3) na divisão do [planejamento](planejamento.md). Ele limita os comandos às suas células.
- **`situacao`** mostra, para cada célula (tipo × período), quantas páginas foram listadas e quantas capturadas. Sem `--pessoa`, mostra a amostra inteira.
- **`listar`** e **`capturar`** são retomáveis. Se parar, rode de novo e o script continua de onde estava, sem repetir nenhuma página.
- **Várias pessoas** podem rodar o `capturar` ao mesmo tempo. O banco nunca entrega a mesma página a duas.
- **Listas extras:** `--complemento` e `--cobertura` sorteiam de modo equilibrado por ano (uma página de cada ano por rodada). `--cobertura` usa as páginas dos anos pouco cobertos, como 1886 a 1888.
- **Imagens:** o `capturar` do script guarda as imagens em `data/amostra/` (uns 6 MB por página). Com elas, o `reprocessar` pode refazer o OCR; a separação em anúncios já não depende delas.
- Os passos abaixo explicam cada comando por dentro, para quem quiser ir além da amostra.

## Passo a passo

Os passos abaixo explicam cada comando. Para refazer tudo de uma vez depois de uma captura, veja [Rodar tudo de uma vez](#rodar-tudo-de-uma-vez-rodar_tudopy).

### 1. Escolher o termo e o acervo

O **acervo** é um jornal num intervalo de anos, identificado por um código (`bib`). Os mais usados:

| Código | Jornal | Anos |
|---|---|---|
| `364568_01` | Jornal do Commercio (RJ) | 1827–1829 |
| `364568_02` | Jornal do Commercio (RJ) | 1830–1839 |
| `364568_03` | Jornal do Commercio (RJ) | 1840–1849 |
| `364568_04` | Jornal do Commercio (RJ) | 1850–1859 |
| `364568_05` | Jornal do Commercio (RJ) | 1860–1869 |
| `364568_06` | Jornal do Commercio (RJ) | 1870–1879 |
| `364568_07` | Jornal do Commercio (RJ) | 1880–1889 |
| `094170_01` | Diário do Rio de Janeiro | 1821–1858 |
| `094170_02` | Diário do Rio de Janeiro | 1860–1878 |

A lista completa e as contagens de cada termo estão em [termos_busca.md](termos_busca.md). Para achar o código de outro jornal, abra-o no site da HDB: o código aparece no endereço, depois de `bib=`.

### 2. Listar as páginas: `buscar`

```bash
$PY -m hdb buscar --bib 364568_04 --termo '"escrav* fugid*"' --limite 100
```

- `--termo`: frases vão entre aspas duplas, e o conjunto entre aspas simples, como no exemplo.
- `--limite`: quantas ocorrências listar. Sem ele, lista todas.
- **O que acontece:** a ferramenta abre a busca na HDB e anda de página em página, gravando cada uma como `pendente`. Não pede CAPTCHA. Leva cerca de 3,6 segundos por página.
- **Resultado:** `100 de 671 ocorrências de '"escrav* fugid*"' no banco.`
- Se cair no meio, rode o mesmo comando de novo: ele continua de onde parou.
- Se o site bloquear de vez, o comando espera e, persistindo o bloqueio, para com a mensagem "tente de novo mais tarde" e código de saída `2`. O que já foi gravado fica; é só rodar de novo depois.

### 3. Capturar, ler e separar: `capturar`

```bash
$PY -m hdb capturar --bib 364568_04 --termo '"escrav* fugid*"' --aleatorio --max-paginas 30 --quem ana --guardar-imagens data/amostra
```

| Opção | O que faz |
|---|---|
| `--bib`, `--termo` | só páginas deste acervo e deste termo |
| `--aleatorio` | sorteia as páginas; sem ela, segue a ordem do jornal |
| `--max-paginas` | quantas páginas nesta execução (padrão 50) |
| `--quem` | seu nome, para o banco saber quem capturou (padrão: usuário do computador) |
| `--guardar-imagens DIR` | guarda uma cópia de cada imagem (~3,5 MB por página). Não é mais preciso para separar os anúncios (isso sai do OCR, no banco); serve para guardar a imagem, por exemplo para `reprocessar` |
| `--equilibrar` | sorteia uma página de cada ano por rodada, para os anos ficarem uniformes (o complemento também sai assim) |
| `--sem-segmentar` | não separa os anúncios na hora; depois rode `anuncios` |
| `--modo janela` | mostra o navegador; o CAPTCHA é digitado na própria janela |
| `--workers` | quantas leituras de OCR ao mesmo tempo (padrão 4; mais que isso pode faltar memória) |

**Quando aparecer o CAPTCHA** (modo padrão):
1. O terminal mostra `CAPTCHA: abra file:///.../data/captura/captcha.png e digite o código`.
2. Abra a imagem (no VS Code, Ctrl+clique no caminho) e digite os números.
3. Enter sem nada troca a imagem do código, se estiver ilegível.
4. Se errar, ele avisa "Código incorreto" e pede de novo.

**Durante a captura,** cada página aparece como `364568_04 p.40: ok` ou com o erro. No fim:

```
Resumo: 28 ok, 2 erros, 1 CAPTCHAs resolvidos (páginas por CAPTCHA: 28.0).
```

**Para parar, use Ctrl+C.** O que já foi gravado fica, e o resto volta para a fila.

**Se o site bloquear (429 ou 503) durante a captura:** quando a imagem não aparece e o site responde com bloqueio, a página **não é marcada como erro e não gasta tentativa**. Ela volta para a fila, e a captura para com a mensagem "tente de novo mais tarde" e código de saída `2`. Nada é resolvido sozinho: o CAPTCHA continua sendo digitado por uma pessoa.

Cada página leva em média uns 40 segundos, quase tudo de OCR. Páginas de jornais mais densos (anos 1880) levam mais.

### 4. Separar os anúncios: `anuncios`

```bash
$PY -m hdb anuncios --pasta data/amostra --depurar data/depuracao/paginas
```

- **A captura já separa os anúncios** e grava as palavras do OCR no banco (tabela `paginas_palavras`, uns 50 KB por página). Este comando serve para o que ficou de fora: **pula as páginas que já têm anúncios nessa versão**. Com `--refazer`, reprocessa todas.
- Com `capturar --sem-segmentar`, a captura não separa; rode este comando depois.
- Página sem imagem, mas com palavras no banco, é separada a partir do banco.
- Se a página não tem palavras no banco, precisa da imagem em disco. Na primeira vez, refaz o OCR para obter a posição das palavras e guarda em `data/ocr_palavras/`. Nas seguintes, usa essa cópia e leva segundos.
- Quem já tem `data/ocr_palavras/` no computador pode mandar essas palavras ao banco, sem OCR novo: `$PY -m hdb palavras --subir` (opcional `--pasta`). Depois, rode `anuncios` e `campos`.
- **Resultado por página:** `364568_03 p.44: 4 colunas, 622 segmentos, 66 anúncios, 24 com abertura, 14 com título`.
- `--depurar DIR` cria uma imagem por página com as colunas (linhas vermelhas) e cada anúncio num retângulo numerado. É a melhor forma de conferir se a separação funcionou.
- `--versao` (padrão `v2`) dá nome à versão da regra. Rodar de novo a mesma versão substitui os anúncios dela; uma versão nova convive com as antigas, o que permite comparar.
- **`--do-texto` (segmentação só pelo texto, versão `v2t`):** segmenta, sem imagem e sem posições das palavras, as páginas que têm o texto do OCR no banco e ainda não têm anúncios `v2`. Grava o resultado como `v2t`, ao lado da `v2`. Com `--bib`, limita aos acervos indicados: `$PY -m hdb anuncios --do-texto --bib 364568_01 364568_02`.
- **Quando vale:** páginas de poucas colunas e anúncios numerados, como o Diário do Rio e o Jornal do Commercio dos anos 1820 e 1830. Por isso foi aplicada só aos acervos `364568_01` e `364568_02`.
- **Quando não vale:** jornais de várias colunas, como o JC dos anos 1860. O Tesseract emenda linhas de colunas vizinhas e a separação fica bem pior. Essas páginas esperam a imagem, para a separação com posições.
- `scripts/validar_texto.py` compara a `v2t` com a `v2` das mesmas páginas, só lendo o banco. A meta de 70% de concordância vale só para o Diário do Rio.
- `hdb campos`, o resumo e os cadernos leem as duas versões (`v2` e `v2t`).

### 5. Ver o andamento: `status`

```bash
$PY -m hdb status
```

Mostra quantas páginas há em cada situação (por acervo e por termo), os últimos erros e quantas páginas foram capturadas por CAPTCHA.

### 6. Descobrir os periódicos de um estado: `acervos`

```bash
$PY -m hdb acervos --local RJ --periodo "1850 - 1859"
```

- Serve para saber **quais jornais** a HDB tem no Rio de Janeiro nos anos 1850 e qual é o código (`bib`) de cada um.
- A ferramenta abre a tela de busca, percorre a lista de periódicos um a um e grava o código e os anos de cada.
- `--sonda` é a palavra usada para abrir cada periódico (padrão: `janeiro`, `rio`, `anno`). Repita a opção para dar reservas: `--sonda janeiro --sonda rio`.
- `--limite 10` consulta só 10 periódicos nesta execução, bom para testar. `--modo janela` mostra o navegador.
- Se parar no meio, rode de novo: continua de onde parou.
- Se a tela pedir CAPTCHA, a ferramenta **para** e avisa. Ela não o resolve.

### 7. Ver o panorama: `panorama`

```bash
$PY -m hdb panorama --local RJ --periodo "1850 - 1859" --termo '"escrav* fugid*"'
```

- Conta, em cada periódico da lista, em quantas **páginas** o termo aparece, e mostra um ranking com: posição, periódico, código, anos, páginas com o termo, total de páginas do acervo e percentual.
- Rode antes o `acervos` para o mesmo local e período.
- `--termo` pode ser repetido para vários termos. `--ordenar percentual` ordena pela proporção de páginas, em vez do número de páginas. `--recontar` refaz contagens já guardadas. `--sem-total` não calcula o total de páginas (e, sem ele, não há percentual).
- **Atenção ao aviso "cobre mais que a década":** a HDB conta o acervo inteiro. Um jornal que vai de 1840 a 1869 aparece na lista de 1850, mas a contagem inclui os outros anos.
- Não é preciso CAPTCHA: são só consultas de contagem.

### 8. Extrair os campos dos anúncios: `campos`

```bash
$PY -m hdb campos --versao-anuncios v2 --versao c5
```

- Lê os anúncios já separados (versão `v2`) e, para cada um, grava na tabela `anuncio_campos`:
  - o **tipo**: `fuga`, `venda`, `compra`, `aluguel`, `ama_de_leite` ou `outro` (e `aluguel_incerto`, aluguel sem marca de escravizado, como "criada" ou "rapariga", que fica fora do corpus); e `procura`, que é verdadeiro quando quem anuncia quer obter alguém (COMPRA-SE, PRECISA-SE);
  - **sexo**, **idade** (mínima e máxima), **nações**, **cores**, **condição** (escravizado, forro, livre ou desconhecida), **nomes**, **ofícios**, **recompensa**, **valor** e **endereço**;
  - as **evidências**: o trecho do texto que justificou cada campo, para você conferir.
- Na versão `c5` (a atual), a **fuga** só vale com sinal de pessoa: palavra de pessoa, marca de escravizado, idade, nação, "de nome", sinal do corpo ou da roupa, ou dono. Sem nenhum desses, o anúncio vira `outro`. Também viram `outro` os anúncios de animal, de papel (cautela, bilhete), de remédio e de relato de navio, e "preto livre" explícito. "Cabra" só conta como pessoa com outra marca. A abertura FUGIO, FUGIU ou EVADIO-SE continua fuga mesmo com OCR ruim.
- `--versao` (padrão `c5`, a atual) dá nome à versão da extração. Rodar de novo a mesma versão substitui; uma versão nova convive com as antigas. `--limite 100` processa só 100 anúncios, para testar.
- Não usa internet nem CAPTCHA, só o banco. No fim imprime um resumo: anúncios por tipo e por sexo, quantos têm idade, as nações mais comuns, quantos têm nome e recompensa.

**Limites da extração de campos:**

- É **heurística**: regras sobre palavras, não uma leitura inteligente. O texto vem do OCR de jornais antigos, com grafia da época e letras erradas, então há erros e lacunas.
- **Confira por amostra:** sorteie alguns anúncios e compare cada campo com o texto (use as evidências).
- O **sexo fica vazio** quando o anúncio não tem contexto de pessoa. "Preta" de seda ou "escravo" passageiro de navio, por exemplo, não contam como a pessoa anunciada.
- Quando a separação junta dois anúncios vizinhos num só, os campos saem misturados (sexo `ambos`, por exemplo).
- Anúncios de várias pessoas podem receber o sexo `ambos`, ou nomes e idades misturados.
- Nenhum campo foi conferido por pessoas; não há taxa de acerto medida.

### 9. Padronizar o texto: `corpus`

```bash
$PY -m hdb corpus
$PY -m hdb corpus --incluir-incertos
```

- Escolhe, entre os anúncios com campos (versão `c5`), os de pessoas escravizadas com texto legível, e grava o texto padronizado (sem acento, grafia atual, sem palavras vazias) ao lado do original, em `anuncio_corpus`.
- `--versao` (padrão `corp3`, antes `corp2`) dá nome à versão; regravar a mesma substitui. `--versao-campos` escolhe a versão dos campos usada na seleção.
- **`--incluir-incertos`** inclui os `aluguel_incerto` (aluguel sem marca de escravizado, como "criada") e grava a versão `corp3i`. Serve **só para comparar**: mostra se a conclusão muda quando esses anúncios entram. O corpus principal (`corp3`) não os inclui.
- **Cortes feitos no `corp3`:**
  - `cortar_colado`: quando o OCR colou dois anúncios num pedaço só, fica com o primeiro trecho que tem pessoa. O texto original nunca é alterado.
  - `descobrir_ocr` (em `src/hdb/corpus.py`): acha e aplica os erros de OCR de "perda da primeira letra" (`luga`→`aluga`, `ozinha`→`cozinha`). Os demais candidatos só são listados, para revisão.
- A saída diz quantos anúncios entraram no corpus e quantos foram descartados, com o motivo: tipo `outro`, aluguel sem marca de escravizado, fuga sem sinal de pessoa (`sem_pessoa`), OCR com confiança baixa ou ausente, poucas palavras e texto longo demais (`longo`: mais de 1.500 caracteres, em geral vários anúncios colados). Depois, a contagem por período legal.
- Um anúncio `sem_pessoa` fica fora do modelo de tópicos, mas continua no banco e nos gráficos descritivos.

### 10. Modelar os tópicos: `topicos`

```bash
$PY -m hdb topicos --topicos 6 --versao t5
```

- Roda o LDA sobre o corpus e grava as palavras de cada tópico (`topico_palavras`), a mistura de tópicos de cada anúncio (`anuncio_topicos`) e o registro do modelo (`topico_modelos`), com o nome da versão.
- `--topicos` (padrão 8), `--versao` (padrão `t2`) e `--semente` (padrão 0, para o resultado se repetir). Com `--semente auto`, o programa roda 10 sementes e usa a mais representativa, ou seja, a que mais se parece com as demais. As versões atuais:
  - **`t5`**: 6 tópicos, sobre o corpus `corp3`. É a principal.
  - **`t5i`**: 6 tópicos, sobre o corpus `corp3i` (com os `aluguel_incerto`). Mede a sensibilidade da análise a esses anúncios.
  - **`t4`**: corpus antigo (`corp2`). Fica para comparação.
- A saída tem uma linha com o número de anúncios e a perplexidade. Depois, para cada tópico: quantos anúncios o têm como dominante, as palavras mais fortes e a divisão por período legal e por tipo.
- **Nomes sugeridos:** `hdb.topicos.nomear` dá a cada tópico um nome a partir das suas palavras. É só uma sugestão; quem decide é o grupo.
- **Palavras distintivas** (`src/hdb/distintivas.py`): as palavras que mais distinguem um grupo dos outros (um período, um tipo, um sexo), com um teste estatístico que evita palavras comuns demais. O caderno de mudança por tipo as usa.
- **Períodos de mesmo tamanho** (`topicos.equilibrado`): repete o LDA em sorteios com o mesmo número de anúncios por período e tira a média. O caderno `equilibrio_periodos.ipynb` usa essa função.
- O número de tópicos muda os temas: veja os Cuidados em [linguagem_natural.md](linguagem_natural.md). A estabilidade é medida com `scripts/estabilidade_topicos.py`. A comparação dos períodos está nos notebooks [topicos_por_periodo.ipynb](notebooks/topicos_por_periodo.ipynb) e [analise_descritiva.ipynb](notebooks/analise_descritiva.ipynb).

### 11. Gerar o relatório: `relatorio`

```bash
$PY -m hdb relatorio
$PY -m hdb relatorio --saida relatorios/minha_versao.md
```

- Escreve um arquivo Markdown que explica **como o corpus foi formado**: regras da busca da HDB, termos e acervos, capturas (quem, quantas, CAPTCHAs), OCR, anúncios e campos, panorama, limites conhecidos e créditos.
- Sem `--saida`, o arquivo vai para `relatorios/relatorio_<data>.md`. O comando imprime o caminho.
- Tudo vem do banco: rode depois de capturar ou extrair para o relatório sair atualizado. Serve de base para a seção de método do trabalho.

### 12. Consultar os dados no banco

Os dados ficam no Supabase. No painel do projeto, abra o **SQL Editor** e rode consultas como estas. **Não há exportação em CSV ou JSON pela ferramenta: os dados ficam no banco** e se consultam por SQL.

Anúncios com palavras de interesse:

```sql
select p.bib, p.ano, p.pagina_fisica, a.ordem, a.abertura, a.texto
from anuncios a
join paginas p on p.id = a.pagina_id
where a.versao = 'v2'
  and a.busca @@ to_tsquery('portuguese', 'escravo | preta | crioulo | moleque')
order by p.bib, p.pagina_fisica, a.ordem;
```

A busca em português junta variações: `preta` também acha `preto` e `pretas`.

O texto inteiro de uma página:

```sql
select p.bib, p.pagina_fisica, t.motor, t.confianca, t.texto
from textos_atuais t
join paginas p on p.id = t.pagina_id
where p.bib = '364568_04' and p.pagina_fisica = 320;
```

Ranking do panorama (a view `panorama`):

```sql
select nome_lista, bib, ano_inicio, ano_fim, termo, paginas, total_paginas,
       round(percentual * 100, 2) as pct, cobre_mais_que_a_decada
from panorama
where local = 'RJ' and periodo = '1850 - 1859' and termo = '"escrav* fugid*"'
order by paginas desc;
```

Anúncios de fuga com recompensa, por período legal (a view `anuncios_completos`; filtre sempre por `versao` e `c_versao`):

```sql
select periodo_legal, count(*) as anuncios
from anuncios_completos
where versao = 'v2' and c_versao = 'c5' and c_tipo = 'fuga' and c_recompensa
group by periodo_legal
order by periodo_legal;
```

Anúncios de venda de mulheres, com idade e nação:

```sql
select ano, acervo, c_idade_min, c_idade_max, c_nacoes, c_nomes, c_valor, texto
from anuncios_completos
where versao = 'v2' and c_versao = 'c5' and c_tipo = 'venda' and c_sexo = 'f'
order by ano;
```

Conferir uma amostra de 20 anúncios com o trecho que justificou cada campo:

```sql
select id, c_tipo, c_sexo, c_nacoes, c_evidencias, texto
from anuncios_completos
where versao = 'v2' and c_versao = 'c5'
order by random()
limit 20;
```

## Rodar tudo de uma vez: `rodar_tudo.py`

Depois de uma captura nova (por exemplo, o complemento), não é preciso rodar um comando por vez. O `rodar_tudo.py` refaz a sequência inteira:

```bash
PYTHONPATH=src $PY scripts/rodar_tudo.py
PYTHONPATH=src $PY scripts/rodar_tudo.py --rapido --sem-notebooks
PYTHONPATH=src $PY scripts/rodar_tudo.py --so topicos
```

| Opção | O que faz |
|---|---|
| `--rapido` | pula a estabilidade dos tópicos, que é a parte mais demorada (`--help` mostra a lista completa de opções) |
| `--sem-notebooks` | não refaz os cadernos (o último passo) |
| `--so PASSO` | roda só um passo |

- Os passos, nesta ordem: `campos`, `corpus`, `corpus_i`, `topicos`, `topicos_i`, `estabilidade`, `relatorio`, `resumo`, `notebooks`.
- `resumo` grava o `resumo_dados.md` (uma página, com os números lidos do banco e o mapa de cobertura por ano). `notebooks` gera e executa seis cadernos: análise descritiva, tópicos por período, equilíbrio entre períodos, mudança por tipo, categorias por período e material do grupo.
- O comando **para no primeiro erro**. O registro de cada execução fica em `data/rodar_tudo.log`.
- Os geradores dos cadernos ficam em `scripts/notebooks/`. Os comentários com números são reescritos à mão depois de cada rodada. Cada caderno avisa quando o número de anúncios mudou desde que os comentários foram escritos.

## Outros comandos

| Comando | Para que serve |
|---|---|
| `scripts/avaliar_limpeza.py [arquivo]` | mede a limpeza do corpus contra uma conferência (por padrão, `tests/fixtures/conferencia.json`): quanto ruído sobra, quantos anúncios verdadeiros foram perdidos e se o tipo está certo. Sai com erro se as metas falharem: ruído cair pelo menos 50% e anúncios perdidos até 3%. O grupo pode refazer a conferência com os mesmos arquivos (`conferencia.json` e `conferencia_extra.json`). |
| `rodar_tudo.py` | refaz o fluxo inteiro (veja a seção acima) |
| `reprocessar` | refaz o OCR de imagens guardadas em disco (sem internet nem CAPTCHA) e mostra o antes e depois de cada página. Útil para testar melhorias do OCR. |
| `importar` | carrega no banco dados da primeira versão da ferramenta (arquivos CSV e imagens antigas). Só foi usado uma vez. |
| `palavras --subir [--pasta data/ocr_palavras]` | envia ao banco o cache de palavras do OCR que está no disco (sem OCR novo). Serve para as páginas separadas antes da mudança. |
| `scripts/estabilidade_topicos.py` | mede a estabilidade do LDA por número de tópicos (k) e semente. Use antes de escolher o k. |
| `scripts/contar_termos.py` | conta em quantas páginas cada termo aparece em cada acervo. Para testar termos novos, acrescente-os à lista do arquivo e rode: ele conta só o que falta. |
| `scripts/contar_paginas.py` | conta o total de páginas de cada acervo. |
| `scripts/resumo_dados.py` | grava `resumo_dados.md`: uma página com os números finais, lidos do banco, e o mapa de cobertura (anos sem página). É o passo `resumo` do `rodar_tudo.py`. |
| `scripts/validar_texto.py` | compara a segmentação pelo texto (`v2t`) com a segmentação com posições (`v2`), só lendo o banco. Veja `anuncios --do-texto`. |

Testes automáticos (não usam internet nem banco): `$PY -m pytest`.

## Onde ficam as coisas

**No banco (Supabase):**

| Tabela | O que guarda |
|---|---|
| `acervos` | os jornais (código, nome, anos e total de páginas) |
| `paginas` | cada página: acervo, número, ano, edição, link e status |
| `ocorrencias` | em que página cada termo foi encontrado, e em que posição da busca |
| `textos_ocr` | o texto lido de cada página; uma página pode ter mais de uma leitura (a view `textos_atuais` dá a mais recente) |
| `tentativas` | histórico: quem capturou, quando, quanto tempo levou, quantos CAPTCHAs, e os erros |
| `anuncios` | cada anúncio: página, versão, ordem, coluna, título, palavra de abertura, texto bruto, texto limpo, confiança e posição |
| `acervos_periodos` | a lista de periódicos de cada local e período (posição na lista, nome e código `bib`) |
| `contagens` | em quantas páginas do acervo inteiro cada termo aparece |
| `anuncio_campos` | tipo e campos extraídos de cada anúncio, por versão da extração, com as evidências |
| `anuncio_corpus` | o texto padronizado de cada anúncio do corpus, ao lado do original |
| `topico_modelos` | cada modelo de tópicos rodado, por versão |
| `topico_palavras` | as palavras mais fortes de cada tópico, com o peso |
| `anuncio_topicos` | a mistura de tópicos de cada anúncio |
| `paginas_palavras` | a posição das palavras lidas pelo OCR, por página (uns 50 KB cada); permite separar anúncios sem a imagem |

Quatro "views" (consultas prontas, que se usam como tabelas): `panorama` (o ranking de acervos por termo), `anuncios_completos` (anúncio, página, acervo, período legal e campos juntos), `textos_atuais` (o texto mais recente de cada página) e `topicos_por_periodo` (os tópicos por período legal).

**No computador (pasta `data/`):**

| Pasta | O que tem |
|---|---|
| `data/amostra/` | imagens guardadas com `--guardar-imagens` |
| `data/ocr_palavras/` | posição das palavras de cada página (cópia que evita refazer o OCR) |
| `data/depuracao/` | imagens de conferência da separação de anúncios |
| `data/falhas_ocr/` | imagens em que o OCR falhou |
| `data/tmp/` | imagens à espera do OCR (apagadas depois de gravar no banco) |
| `data/captura/` | o perfil do navegador e a imagem do CAPTCHA |

## Trabalho em grupo

- Cada pessoa usa `--quem` com o próprio nome.
- Podem capturar ao mesmo tempo: o banco reparte as páginas.
- Combinem quem lista quais termos, para não listarem a mesma busca em paralelo (não estraga nada, mas gasta tempo).
- Rodem o `status` antes de começar, para ver o que falta.

## Problemas comuns

| Situação | O que fazer |
|---|---|
| `erro: faltam SUPABASE_URL e SUPABASE_SECRET_KEY` | o arquivo `.env` não está na pasta do projeto ou está incompleto |
| "Código incorreto" no CAPTCHA | digite de novo; Enter vazio troca a imagem |
| A captura parou no meio | rode o mesmo comando: as páginas voltaram para a fila e as imagens que sobraram em `data/tmp/` são lidas primeiro |
| Página com status `erro` de OCR | a imagem está em `data/falhas_ocr/`; teste com `reprocessar --pasta data/falhas_ocr` |
| A captura está lenta | é o OCR; páginas densas levam mais de um minuto |
| Mensagem "tente de novo mais tarde" e código de saída 2 | o site da HDB bloqueou os pedidos. Espere um tempo e rode o mesmo comando de novo; nada foi perdido e as páginas não foram marcadas como erro |
| O `anuncios` não acha imagem nem palavras de uma página | se houver `data/ocr_palavras/` na máquina, rode `palavras --subir`; senão, a imagem precisa estar em disco (`data/amostra/`) |
| O computador ficou sem espaço | as imagens de `data/amostra/` ocupam ~3,5 MB cada. Podem ser apagadas as de páginas que já têm palavras no banco (`anuncios` e `campos` não dependem mais delas). Não apague as das páginas ainda sem separação (planejamento, A1) |

## Limites que convém conhecer

- **O OCR erra letras**, principalmente nas páginas densas de 1850 a 1880, e às vezes pula uma linha encostada numa régua.
- **A extração de campos também é heurística** (veja o passo 8): confira por amostra.
- **A separação de anúncios é heurística:** pode juntar dois anúncios vizinhos ou partir um em dois. As imagens de depuração mostram onde.
- **Os tópicos mudam com o número de tópicos e a semente.** Com poucos anúncios, o LDA é instável. Veja os Cuidados em [linguagem_natural.md](linguagem_natural.md).
- **A busca da HDB conta páginas, não anúncios,** e só acha o que o OCR da própria BN leu certo.
- **Uso responsável:** a ferramenta faz uma pausa fixa entre requisições, para não sobrecarregar a Biblioteca Nacional. Em listagens longas (depois de 200 passos), a pausa passa de 1,5 para 3 segundos. Quando o site pede espera (429 ou 503), a ferramenta espera e, se o bloqueio continuar, para. Nunca contorna o CAPTCHA. Não reduza essas pausas. As constantes estão em `src/hdb/config.py`.

## Termos usados neste guia

| Termo | Significado |
|---|---|
| **acervo** (`bib`) | um jornal num intervalo de anos, ex.: `364568_04` = Jornal do Commercio, 1850–1859 |
| **página física** | o número da página dentro do acervo (não é o número impresso no jornal) |
| **ocorrência** | uma página encontrada por um termo na busca |
| **OCR** | programa que lê o texto de uma imagem |
| **CAPTCHA** | código de imagem que o site pede para provar que há uma pessoa |
| **segmento** | um pedaço de linha dentro de uma coluna |
| **anúncio `largo`** | anúncio que provavelmente pega texto de mais de uma coluna |
| **versão** (`v1`, `v2`, `v2t`) | qual regra de separação de anúncios gerou aquele resultado; `v2t` é a separação só pelo texto do OCR |
| **corpus** | o conjunto final de anúncios que vai para a análise |
| **palavras do OCR** | a posição de cada palavra lida numa página; fica no banco (`paginas_palavras`) para separar os anúncios sem a imagem |
| **modelagem de tópicos** | técnica que agrupa textos por temas que se repetem |
| **palavras distintivas** | palavras que aparecem mais num grupo (período, tipo, sexo) do que nos outros, com teste estatístico |
| **segmentação pelo texto** | separar os anúncios a partir só do texto do OCR, sem as posições das palavras (`v2t`) |
