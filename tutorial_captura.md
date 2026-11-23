# Tutorial rápido: ajudar a capturar os dados

Para quem só vai **capturar páginas** (o trabalho de análise fica com a equipe). Dura uns 5 minutos para começar e depois é repetir.

## O que é capturar

O site da Hemeroteca mostra a imagem de cada página só depois de um **CAPTCHA** (aquelas letras tortas). Você digita o código; o computador baixa a imagem, lê o texto e grava no banco compartilhado. O resto é automático. **Não tente automatizar o CAPTCHA.**

## Uma vez só: preparar o computador

1. Peça ao Diego: o **convite do GitHub** (aceite pelo e-mail) e o arquivo **`.env`** (por mensagem privada, nunca em grupo).
2. No terminal:

```bash
git clone https://github.com/DiegoSamim/projetoDadosCompSoc.git
cd projetoDadosCompSoc
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
sudo apt install tesseract-ocr tesseract-ocr-por
```

3. Coloque o `.env` dentro da pasta `projetoDadosCompSoc`.
4. Teste (tem que aparecer uma tabela, sem erro):

```bash
PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao
```

## Toda vez que for capturar

```bash
cd projetoDadosCompSoc
git pull                                              # 1. pega as novidades
PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar --pessoa N --quem SeuNome
```

- **`N`** é o número que o Diego combinar com você (1, 2 ou 3). Ele diz quais períodos são seus.
- **`SeuNome`** é só para o registro (ex.: `maria`).

## Quando o CAPTCHA aparecer

1. O terminal mostra: `CAPTCHA: abra file:///.../data/captura/captcha.png e digite o código`.
2. Abra essa imagem (clique no caminho no VS Code, ou abra o arquivo).
3. Digite o código e dê Enter.
4. **Se não conseguir ler,** dê Enter sem digitar nada: aparece outro código.
5. Depois disso ele trabalha sozinho por um tempo (cerca de 1 minuto por página).

Fique com o terminal à vista: **se ninguém digitar em 10 minutos, a página dá erro** (não perde nada, mas a página volta para a fila).

## Para acompanhar

```bash
PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao --pessoa N
```

Mostra, para cada tipo de anúncio, quantas páginas já foram capturadas e quantas faltam. **Acabou quando todas as linhas mostram `X de X`.**

## No fim: separar os anúncios

```bash
PYTHONPATH=src .venv/bin/python -m hdb anuncios
PYTHONPATH=src .venv/bin/python -m hdb campos
```

Isso usa as imagens que ficaram no **seu** computador (`data/amostra/`), então **não apague essa pasta** antes de rodar. Demora uns minutos.

## Se der problema

| O que apareceu | O que fazer |
|---|---|
| Parou ou travou | `Ctrl+C` e rode o mesmo comando de novo: continua de onde parou, sem repetir página |
| `faltam SUPABASE_URL…` | o `.env` não está na pasta certa |
| `permission denied` ao subir no git | o convite do GitHub ainda não foi aceito |
| Erro de `tesseract` | o Tesseract em português não foi instalado (passo do `apt install`) |
| Qualquer outro erro | copie as últimas linhas e mande para o Diego |

## Regras

- **Nunca** suba o `.env` nem a pasta `data/` para o git.
- Você **não precisa** dar `git push` para a captura funcionar: os dados vão direto para o banco. O `git` só é usado para pegar código novo (`git pull`).

## O que ler, se quiser entender melhor

| Ordem | Documento | Para quê |
|---|---|---|
| 1 | [README.md](README.md), seção "Trabalhar no repositório" | rotina do git |
| 2 | [planejamento.md](planejamento.md), seção "Situação em 23/11" | o que falta e quem faz o quê |
| 3 | [guia_ferramenta.md](guia_ferramenta.md), "O caminho recomendado" e "Problemas comuns" | cada comando por dentro |
| 4 | [notebooks/como_funciona.ipynb](notebooks/como_funciona.ipynb) | o caminho inteiro com dados reais |
| só se tiver curiosidade | [termos_busca.md](termos_busca.md), [linguagem_natural.md](linguagem_natural.md) | por que estas frases; como serão os tópicos |
