# Planejamento do projeto

**Objetivo:** reunir algumas centenas de anúncios de pessoas escravizadas do Jornal do Commercio (RJ), de antes de 1831 até 1888, encontrar os **temas** que se repetem neles (modelagem de tópicos) e comparar esses temas entre os períodos das leis de 1831, 1850, 1871, 1885 e 1888.

Detalhes, quando precisar: [termos_busca.md](termos_busca.md) (por que estes termos) · [guia_ferramenta.md](guia_ferramenta.md) (como usar cada comando) · [linguagem_natural.md](linguagem_natural.md) (como funcionam os tópicos) · [notebooks/como_funciona.ipynb](notebooks/como_funciona.ipynb) (exemplo com dados reais).

---

## O que vamos usar (decidido)

| Item | Decisão |
|---|---|
| **Fonte** | Hemeroteca Digital Brasileira, `memoria.bn.gov.br` |
| **Jornal** | Jornal do Commercio (RJ), um acervo por período |
| **Tipos de anúncio** | fuga, venda, aluguel, ama de leite, compra |
| **Termos** | 1 frase por tipo e período: 20 "células" (tabela abaixo), guardadas em `scripts/amostra.py` |
| **Tamanho** | 69 páginas novas, mais as 39 que já estão no banco, para algumas centenas de anúncios |
| **Ferramenta** | `hdb` + `scripts/amostra.py`; tudo fica no banco (Supabase), sem exportar arquivos |
| **Texto** | OCR com Tesseract (já funciona); nada é transcrito à mão |
| **Técnica de tópicos** | **LDA** (`scikit-learn`), um modelo para todos os anúncios, de 6 a 10 tópicos; o período entra na comparação |
| **Comparação** | % de cada tópico por período legal, e por sexo e idade (campos já extraídos) |

**Fora do escopo:**

- capturar milhares de páginas;
- outros jornais e estados;
- transcrição ou rotulagem à mão;
- exportar CSV ou JSON;
- BERTopic (só se sobrar tempo no fim);
- melhorias finas do OCR.

---

## Quem faz o quê

Cada pessoa fica com um ou dois **períodos legais**. Ela coleta os anúncios do seu período, estuda as leis dele e apresenta os resultados dele. A Pessoa 1 cuida também da ferramenta.

| Pessoa | Período | Acervo | Leis para contextualizar | Páginas a capturar | CAPTCHAs (aprox.) |
|---|---|---|---|---:|---:|
| **Pessoa 1** (sugestão: quem cuida da ferramenta) | 1871–1888 | JC 1870s (`364568_06`) | Ventre Livre (1871), Sexagenários (1885), Áurea (1888) | 18 | 5 |
| **Pessoa 2** | antes de 1831 e 1831–1850 | JC 1827–29 (`364568_01`) e JC 1830s (`364568_02`) | Lei Feijó (1831) | 33 | 10 |
| **Pessoa 3** | 1850–1871 | JC 1860s (`364568_05`) | Lei Eusébio de Queirós (1850) | 18 | 5 |

A Pessoa 2 tem mais páginas, mas dois acervos pequenos e, na Fase 3, uma tarefa curta.

### Os dados de cada pessoa

O número depois do termo é quantas páginas capturar.

| Tipo | Pessoa 2: antes de 1831 (JC 1827–29) | Pessoa 2: 1831–1850 (JC 1830s) | Pessoa 3: 1850–1871 (JC 1860s) | Pessoa 1: 1871–1888 (JC 1870s) |
|---|---|---|---|---|
| Fuga | `"escravos fugidos"` · 4 | `"escravos fugidos"` · 4 | `"fugio o escravo"` · 4 | `"fugio o escravo"` · 4 |
| Venda | `"vende-se uma preta"` · 4 | `"vende-se uma preta"` · 4 | `"vende-se uma preta"` · 4 | `"vende-se uma preta"` · 4 |
| Aluguel | `"aluga-se uma preta"` · 3 | `"aluga-se uma preta"` · 4 | `"aluga-se uma escrava"` · 4 | `"aluga-se uma escrava"` · 4 |
| Ama de leite | `"preta com leite"` · 3 | `"preta com leite"` · 4 | `"preta com leite"` · 4 | `"preta com leite"` · 4 |
| Compra | `"compra-se escravos"` · 1 | `"compra-se um moleque"` · 2 | `"compra-se escravos"` · 2 | `"compra-se escravos"` · 2 |

As **39 páginas já capturadas** (Diário do RJ de 1821, Diário Fluminense de 1825–1831 e Jornal do Commercio dos anos 1840, 1850, 1860 e 1880) entram no corpus de todos.

---

## Antes de começar (cada pessoa, uma vez)

1. Preparar o computador conforme o [guia](guia_ferramenta.md), seção "O que precisa estar pronto": Python, `requirements.txt`, Chromium do Playwright e Tesseract em português.
2. Receber o arquivo `.env` da Pessoa 1, **por um canal privado** (nunca em grupo ou mensagem pública).
3. Conferir que tudo funciona: `PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao --pessoa N` mostra a sua tabela.

---

## Fase 1: Pegar os dados

As três pessoas trabalham ao mesmo tempo, cada uma nas suas células. O banco nunca entrega a mesma página a duas pessoas.

| Pessoa | Faz | Comando | Tempo | Pronto quando |
|---|---|---|---|---|
| **1** | Lista e captura 1871–1888 | `scripts/amostra.py listar --pessoa 1`, depois `capturar --pessoa 1 --quem Nome` | listar ~20 min (sozinho); capturar ~1 h, digitando ~5 CAPTCHAs | `situacao --pessoa 1` mostra 18 de 18 |
| **2** | Lista e captura antes de 1831 e 1831–1850 | `scripts/amostra.py listar --pessoa 2`, depois `capturar --pessoa 2 --quem Nome` | listar ~45 min (sozinho); capturar ~1,5 h, digitando ~10 CAPTCHAs | `situacao --pessoa 2` mostra 33 de 33 |
| **3** | Lista e captura 1850–1871 | `scripts/amostra.py listar --pessoa 3`, depois `capturar --pessoa 3 --quem Nome` | listar ~35 min (sozinho); capturar ~1 h, digitando ~5 CAPTCHAs | `situacao --pessoa 3` mostra 18 de 18 |

Os comandos começam com `PYTHONPATH=src .venv/bin/python`. Se algo parar, rode o mesmo comando de novo: ele continua de onde estava, sem repetir páginas.

**Fase 1 pronta quando:** `scripts/amostra.py situacao` (sem `--pessoa`) mostra **69 de 69**.

---

## Fase 2: Agrupar (páginas → anúncios → corpus)

| Pessoa | Faz | Comando ou atividade | Pronto quando |
|---|---|---|---|
| **1, 2 e 3** | Separa os anúncios das **próprias** páginas. As imagens ficam no computador de quem capturou. | `hdb anuncios` | o comando termina sem erro |
| **1** | Extrai os campos de todos os anúncios (tipo, sexo, idade, nação, nome) | `hdb campos` | o resumo mostra os 5 tipos em todos os períodos |
| **1, 2 e 3** | Olha **10 anúncios** do próprio período, uns 15 minutos, e anota os erros grosseiros (tipo errado, dois anúncios grudados). Não é rotular: é ver se dá para confiar. | consulta "Conferir uma amostra" no [guia](guia_ferramenta.md), passo 10, com `limit 10` e o filtro do próprio período | anotações enviadas à Pessoa 1 |
| **1** | Prepara o corpus padronizado (grafia, palavras vazias, corte de qualidade) | `hdb corpus` (construído na Fase 3) | o corpus está no banco, com anúncios nos 4 períodos |
| **1** | Roda o LDA e grava os tópicos | `hdb topicos` (construído na Fase 3) | cada tópico tem palavras e anúncios-exemplo no banco |

**Fase 2 pronta quando:** os tópicos estão no banco e cada pessoa consegue ver os do seu período.

---

## Fase 3: Criar o que falta na ferramenta

A Fase 3 corre **junto com a Fase 1**, enquanto as capturas rodam.

| Pessoa | Faz | Por quê | Pronto quando |
|---|---|---|---|
| **1** | **Separação v3:** usar o travessão ("— DESEJA-SE…") como divisor de anúncios | hoje dois ou três anúncios vizinhos às vezes saem grudados | os anúncios grudados do exemplo 5941 saem separados |
| **1** | **`hdb corpus`:** filtra os anúncios relevantes, aplica o corte de qualidade e grava o texto padronizado | entrada do LDA | o comando roda nos anúncios atuais |
| **1** | **`hdb topicos`:** roda o LDA (`scikit-learn`) e grava os tópicos e a mistura de cada anúncio | é o resultado do projeto | o comando roda e o resultado se repete ao rodar de novo |
| **2** | **Lista de grafias da época** para a padronização. Exemplos: `hum`→`um`, `huma`→`uma`, `annos`→`anos`, `fugio`→`fugiu`, `ph`→`f`. Tirar dos anúncios do próprio período, que são os de grafia mais antiga. | sem isso, a mesma palavra se espalha em várias grafias | lista com umas 50 trocas, entregue à Pessoa 1 |
| **3** | **Lista de palavras vazias**, que aparecem em todo anúncio e não dizem nada: `rua`, `casa`, `trata`, `n`, `largo`… | sem isso, os tópicos saem cheios de endereço | lista com umas 50 palavras, entregue à Pessoa 1 |
| **3** | **Testar o guia:** seguir os comandos da Fase 1 como usuário novo e apontar o que não ficou claro | o guia precisa funcionar para quem não programou a ferramenta | correções anotadas e repassadas |

**Fase 3 pronta quando:** `hdb corpus` e `hdb topicos` funcionam com as listas das Pessoas 2 e 3.

---

## Fase final: Análise e apresentação

| Pessoa | Faz | Entrega |
|---|---|---|
| **1, 2 e 3** | Lê os tópicos e uns 5 anúncios de cada um, dá nome aos tópicos e compara o próprio período com os outros | nomes dos tópicos e o que muda no período |
| **1, 2 e 3** | Contextualização histórica das leis do próprio período, com apoio da dissertação indicada pela Fernanda | resumo de 1 página |
| **1, 2 e 3** | De 2 a 3 slides do próprio período: tópicos, exemplos de anúncios, contexto | slides |
| **1** | Gera o relatório metodológico (`hdb relatorio`) e junta os slides | relatório e apresentação final |

---

## Ordem e dependências

```
Antes de começar (todos)
      │
      ├── Fase 1: listar e capturar (1, 2 e 3 em paralelo)
      │
      └── Fase 3: v3, corpus e tópicos (Pessoa 1) · grafias (Pessoa 2) · palavras vazias e teste do guia (Pessoa 3)
      │
      ▼
Fase 2: anuncios (todos) → campos, corpus, topicos (Pessoa 1) → olhar 10 anúncios (todos)
      │
      ▼
Fase final: nomear tópicos, contextualizar, slides (todos)
```

---

## O que já está pronto

- **Busca na HDB:** termos contados, frases escolhidas e panorama do RJ 1850–1859 feito (o Jornal do Commercio é o jornal certo).
- **Captura com CAPTCHA por pessoa:** OCR local e banco compartilhado sem retrabalho. 39 páginas já estão no banco.
- **Separação dos anúncios:** 3.796 anúncios, 347 deles de pessoas escravizadas.
- **Extração de campos:** tipo, sexo, idade, nação, nome, recompensa e período legal.
- **Relatório metodológico, notebook didático e script da amostra.**
- **286 testes automáticos.**

## Riscos

| Risco | O que fazer |
|---|---|
| O site muda ou o CAPTCHA aparece a cada página | capturar menos páginas por célula (de 2 a 3) e avisar a Pessoa 1 |
| Uma célula tem poucas páginas boas | aceitar menos; o corpus de todas as células junto ainda compara os períodos |
| Tópicos confusos por ruído do OCR | reforçar as listas de grafias e de palavras vazias e rodar de novo com outro número de tópicos |
| O plano gratuito do Supabase enche | improvável com cerca de 110 páginas; a Pessoa 1 acompanha |
