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

## Situação em 23/11 e plano para terminar hoje

### O que os dados mostram (atualizado em 23/11, à noite)

| | Hoje | Meta |
|---|---|---|
| Páginas capturadas (amostra completa: **69 de 69**) | **108** | amostra + extras + complemento |
| Páginas com anúncios separados | **59 de 108** | todas |
| Anúncios de pessoas escravizadas (tipo ≠ outro) | **676** | pelo menos 100 por período legal |

**Anúncios relevantes por período (das 59 páginas já separadas):**

| Período | Relevantes | Fuga | Venda | Aluguel | Ama de leite | Compra | Situação |
|---|---:|---:|---:|---:|---:|---:|---|
| antes de 1831 | **28** | 28 | 0 | 0 | 0 | 0 | **fraco** (só fuga; 15 páginas do JC 1827–29 ainda sem separar) |
| 1831–1850 | 136 | 26 | 54 | 35 | 18 | 3 | ok (18 páginas do JC 1830s ainda sem separar) |
| 1850–1871 | 203 | 34 | 51 | 93 | 22 | 3 | ok (16 páginas do JC 1860s ainda sem separar) |
| 1871–1888 | 309 | 33 | 58 | **201** | 13 | 4 | ok em volume; **fuga fraca e aluguel a conferir** |

**O que isso quer dizer:**

1. **A separação das 49 páginas novas continua pendente** (JC 1827–29: 15, JC 1830s: 18, JC 1860s: 16). A separação precisa da imagem, e essas imagens estão no computador de quem capturou. É o que mais muda os números, sobretudo "antes de 1831".
2. **Corrigi uma estimativa:** eu tinha previsto cerca de 4 anúncios por página nos anos 1870. A medida real é **18 por página** (325 anúncios em 18 páginas). Os anos 1860 e 1880 continuam baixos (cerca de 4 por página), então a baixa densidade não é regra das décadas tardias.
3. **Anúncios repetidos são raros nesta amostra:** só cerca de 0,5% repetem o início do texto. O risco existe, mas é pequeno enquanto as páginas forem sorteadas. Tratar duplicatas deixa de ser urgente.
4. **Pendências de qualidade:** 201 "aluguéis" em 1871–1888 é um número alto e **não foi conferido**; pode haver anúncios de aluguel de outra coisa classificados como de pessoas. Também há 56 anúncios com menos de 60 caracteres (fragmentos).
5. **A captura vai bem:** cerca de 63 s por página, uma página de cada 5 com CAPTCHA.

### O que fazer hoje, em ordem

**Bloco 1: destravar (primeira hora)**

| # | Quem | O quê | Pronto quando |
|---|---|---|---|
| 1 | **Quem capturou as 49 páginas** | `git pull`, depois `hdb anuncios` e `hdb campos` no computador com as imagens (`data/amostra/`). É a saída imediata, sem código novo. | `situacao` e a consulta por período mostram anúncios nas páginas de 364568_01, _02 e _05 |
| 2 | **Pessoa 1** | Em paralelo, **3.1**: a captura passa a separar os anúncios na hora e a guardar as posições das palavras no banco. Assim ninguém depende das imagens de outra pessoa, nem depois de melhorar a separação. | uma captura nova já sai com anúncios; `hdb anuncios` refaz a separação a partir do banco |
| 3 | **Pessoa 1** | Liberar as reservas travadas e refazer as 2 páginas com CAPTCHA esgotado (`hdb status` mostra). | nenhuma página reservada há mais de 30 min |

**Bloco 2: completar e equilibrar os dados (meio do dia)**

| # | Quem | O quê | Pronto quando |
|---|---|---|---|
| 4 | **Pessoa 1** | Terminar o período 1871–1888: `capturar --pessoa 1` (faltam as 18 páginas) | `situacao --pessoa 1` mostra 18 de 18 |
| 5 | **Pessoa 3** | Terminar a compra de 1850–1871 (faltam 2 páginas) | `situacao --pessoa 3` mostra 18 de 18 |
| 6 | **Quem estiver livre** | **Páginas extras** onde os dados são fracos (tabela abaixo). Só depois da separação do bloco 1, para ver quanto cada período já tem. | cada período tem pelo menos 100 anúncios relevantes |

**Páginas extras (só se, depois do bloco 1, o período ficar abaixo de 100 anúncios relevantes).** São cerca de 20 páginas a mais, 4 CAPTCHAs:

| Período | Acervo | Termo | Páginas extras |
|---|---|---|---:|
| 1871–1888 | JC 1880s (`364568_07`) | `"escrav* fugid*"` | 8 |
| 1871–1888 | JC 1870s (`364568_06`) | `"vende-se uma preta"` e `"preta com leite"` | 4 + 4 |
| antes de 1831 | JC 1827–29 (`364568_01`) | `"escravos fugidos"` | 4 (fuga que ainda é só do Diário do RJ) |

Essas linhas entram em `scripts/amostra.py` como novas células, e os comandos são os mesmos.

**Bloco 3: categorizar (tarde)**

| # | Quem | O quê | Pronto quando |
|---|---|---|---|
| 7 | **Pessoa 1** | **Tirar duplicatas** (anúncios repetidos entre edições): comparar textos parecidos e manter um por grupo, guardando quantas vezes saiu. Também juntar fragmentos de título em página de letra grande. | o anúncio do "preto Thomé" aparece uma vez |
| 8 | **Pessoa 1** | `hdb campos` em todos os anúncios (versão `c2`) | o resumo mostra os 5 tipos em todos os períodos |
| 9 | **Pessoas 1, 2 e 3** | **Conferir 10 anúncios** do próprio período (15 min) e anotar os erros de tipo, de sexo e de anúncios grudados | anotações entregues; se o tipo estiver certo em 8 de 10, seguimos |
| 10 | **Pessoa 2** | Lista de grafias da época (`hum`→`um`…) | ~50 trocas entregues |
| 11 | **Pessoa 3** | Lista de palavras vazias (`rua`, `casa`, `trata`…) | ~50 palavras entregues |

**Bloco 4: analisar e fechar a ferramenta (próximos dias)**

| # | Quem | O quê |
|---|---|---|
| 12 | **Pessoa 1** | `hdb corpus` (filtro, corte de qualidade, texto padronizado) e `hdb topicos` (LDA, de 6 a 10 tópicos) |
| 13 | **Pessoas 1, 2 e 3** | Nomear os tópicos do próprio período, comparar entre períodos e por sexo e idade |
| 14 | **Pessoa 1** | `hdb relatorio`, contextualização e slides |

**Para "terminar hoje", o corte é:** blocos 1 e 2 completos, e o bloco 3 com as duplicatas tratadas e as conferências feitas. Os blocos 3 (listas) e 4 começam em seguida.

### Riscos de hoje

- **O dado de 1871–1888 é o mais fraco** (letra miúda e OCR ruim). Se, mesmo com as páginas extras, ele ficar abaixo de 100, comparamos esse período com ressalva, dizendo que tem menos anúncios.
- **Se a separação das 49 páginas der muito ruído** (como nas páginas de letra grande dos anos 1860), ela entra na lista de correções antes do `hdb corpus`.
- **Um CAPTCHA parado trava a captura por 10 minutos.** Quem captura deve ficar com o terminal à vista.

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
- **Captura com CAPTCHA por pessoa:** OCR local e banco compartilhado sem retrabalho. **88 páginas** no banco (49 da amostra, capturadas por uma pessoa do grupo desde 20/11, e 39 anteriores).
- **Separação dos anúncios:** 3.796 anúncios em 39 páginas, 347 deles de pessoas escravizadas. **Faltam as 49 páginas novas** (ver "Situação em 23/11").
- **Extração de campos:** tipo, sexo, idade, nação, nome, recompensa e período legal.
- **Relatório metodológico, notebook didático, script da amostra (com `--pessoa`) e repositório no GitHub.**
- **286 testes automáticos.**

## Riscos

| Risco | O que fazer |
|---|---|
| O site muda ou o CAPTCHA aparece a cada página | capturar menos páginas por célula (de 2 a 3) e avisar a Pessoa 1 |
| Uma célula tem poucas páginas boas | aceitar menos; o corpus de todas as células junto ainda compara os períodos |
| Tópicos confusos por ruído do OCR | reforçar as listas de grafias e de palavras vazias e rodar de novo com outro número de tópicos |
| O plano gratuito do Supabase enche | improvável com cerca de 110 páginas; a Pessoa 1 acompanha |
