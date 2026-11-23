# Tutorial rápido: capturar as páginas

Para quem **só vai capturar** (a análise fica com a equipe). Você não precisa entender o código nem mexer no git: é preparar uma vez e rodar **um comando**.

**O que acontece:** o site da Hemeroteca só mostra a imagem de cada página depois de um **CAPTCHA** (letras tortas). Você digita o código; o computador baixa a imagem, lê o texto e grava no banco compartilhado. O resto é automático. Nunca tente resolver o CAPTCHA por programa.

## Parte 1: preparar (uma vez só, uns 10 minutos)

Use o terminal do Linux/Ubuntu (no Windows, o terminal do WSL).

**1. Peça ao Diego o arquivo `.env`**, por mensagem privada (nunca em grupo). Ele é a chave do banco.

**2. Copie e cole estes comandos, um bloco por vez:**

```bash
git clone https://github.com/DiegoSamim/projetoDadosCompSoc.git
cd projetoDadosCompSoc
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
sudo apt install tesseract-ocr tesseract-ocr-por
```

**3. Coloque o arquivo `.env` dentro da pasta `projetoDadosCompSoc`.**

**4. Teste.** Tem que aparecer uma tabela, sem erro:

```bash
PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao
```

## Parte 2: capturar (toda vez)

**1. Abra o terminal na pasta e rode:**

```bash
cd projetoDadosCompSoc
git pull
PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar
```

Esse comando pega **sozinho o que ainda falta**. Você não escolhe nada.

**2. Quando aparecer `CAPTCHA: abra file:///...captcha.png e digite o código`:**

1. abra essa imagem (no VS Code, clique no caminho);
2. digite as letras e dê Enter;
3. se não conseguir ler, dê Enter sem digitar: vem outro código.

**3. Espere.** Ele trabalha sozinho, cerca de 1 minuto por página, e pede um novo CAPTCHA de vez em quando (mais ou menos a cada 5 páginas).

**4. Fique com o terminal à vista.** Se ninguém digitar o CAPTCHA em 10 minutos, aquela página dá erro. Nada se perde: ela volta para a fila.

**5. Acabou** quando o comando terminar e mostrar a tabela com `Capturadas: 69 de 69` (ou quando você quiser parar: `Ctrl+C`).

**Parar e continuar depois não tem problema.** Rode o mesmo comando de novo: ele continua de onde parou e nunca repete uma página.

## Parte 3: no final (uma vez)

```bash
PYTHONPATH=src .venv/bin/python -m hdb anuncios
PYTHONPATH=src .venv/bin/python -m hdb campos
```

Isso separa os anúncios das páginas que **você** capturou. Usa as imagens que ficaram no seu computador, na pasta `data/amostra/`: **não apague essa pasta antes**. Demora uns minutos.

## Se der problema

| O que apareceu | O que fazer |
|---|---|
| Travou ou deu erro no meio | `Ctrl+C` e rode o mesmo comando de novo |
| `faltam SUPABASE_URL…` | o `.env` não está dentro da pasta `projetoDadosCompSoc` |
| Erro falando de `tesseract` | falta o passo `sudo apt install tesseract-ocr tesseract-ocr-por` |
| Erro falando de `playwright` ou `chromium` | falta o passo `playwright install chromium` |
| Qualquer outra coisa | copie as últimas linhas do terminal e mande para o Diego |

## Regras

- **Nunca** compartilhe o `.env`.
- Você **não precisa** subir nada no git. Os dados vão direto para o banco. O `git pull` só serve para pegar código novo.

## Quer entender melhor? (opcional)

| Ordem | Documento | Para quê |
|---|---|---|
| 1 | [planejamento.md](planejamento.md), seção "Situação em 23/11" | o que falta e por quê |
| 2 | [guia_ferramenta.md](guia_ferramenta.md) | cada comando por dentro e os problemas comuns |
| 3 | [notebooks/como_funciona.ipynb](notebooks/como_funciona.ipynb) | o caminho inteiro com dados reais |
