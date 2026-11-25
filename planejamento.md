# Planejamento do projeto

**Objetivo:** reunir algumas centenas de anúncios de pessoas escravizadas do Jornal do Commercio (RJ), de antes de 1831 até 1888, encontrar os **temas** que se repetem neles (modelagem de tópicos) e comparar esses temas entre os períodos das leis de 1831, 1850, 1871, 1885 e 1888.

Detalhes, quando precisar: [termos_busca.md](termos_busca.md) (por que estes termos) · [guia_ferramenta.md](guia_ferramenta.md) (cada comando) · [linguagem_natural.md](linguagem_natural.md) (como funcionam os tópicos) · notebooks em [notebooks/](notebooks/) · [relatório metodológico](relatorios/).

**Atualizado em 25/11/2026.** Este documento tem três partes: o que está **feito**, o que **falta** e as **melhorias** possíveis.

---

## Em cinco linhas

1. A coleta fechou: **158 páginas** no banco, a amostra planejada está **completa (69 de 69)**, mais os extras.
2. **Faltam separar só 16 páginas** do JC dos anos 1860 (várias colunas), e isso só pode ser feito no computador de quem as capturou, porque precisa das imagens. As 33 páginas de 1827–1839 foram separadas só pelo texto (versão `v2t`).
3. A ferramenta já faz tudo, da captura aos **tópicos (LDA)**, e os cadernos rodam com dados reais.
4. A **Etapa 2 da limpeza está feita (25/11)**: regras de tipo (`c5`), corte de anúncios colados, erros de OCR e conferência por amostra, no corpus `corp3` e nos tópicos `t5`. Os números finais saem na próxima rodada. Ainda faltam 1887–1888 e as páginas sem separação.
5. **Próximo passo do grupo:** nomear os tópicos (C2; Etapa 4 do [plano_dados.md](plano_dados.md)) e capturar o complemento (A3). Depois, contextualizar e montar os slides.

---

## Decisões (não mudam)

| Item | Decisão |
|---|---|
| Fonte | Hemeroteca Digital Brasileira, `memoria.bn.gov.br` |
| Jornal | Jornal do Commercio (RJ), um acervo por período; antes de 1831, Diário do RJ e Diário Fluminense |
| Tipos | fuga, venda, aluguel, ama de leite, compra |
| Texto | OCR com Tesseract; nada é transcrito à mão |
| Técnica | **LDA** (`scikit-learn`), um modelo para todos os anúncios; o período entra na comparação |
| Comparação | % de cada tópico por período legal, por sexo, idade e tipo |
| Fora do escopo | milhares de páginas, outros estados, rotulagem à mão, exportar CSV/JSON, melhorias finas do OCR |

---

## Parte 1: O que está feito

### Rodada de 25/11

| Item | Situação |
|---|---|
| Bloqueio do site | **Feito.** A ferramenta espera quando o site pede, para depois de 3 respostas de bloqueio seguidas e não marca página como erro. `hdb buscar`, `amostra.py` e `capturar` param com a mensagem "tente de novo mais tarde" (código de saída 2). |
| Segmentação só pelo texto (`v2t`) | **Feito** nos acervos 364568_01 e 364568_02 (JC 1827–1839). Não foi aplicada ao JC dos anos 1860, de várias colunas. |
| Teto de tamanho do corpus (`longo`) | **Feito.** Texto com mais de 1.500 caracteres, em geral anúncios colados, fica fora do corpus. |
| Guarda da classificação (`c5`) | **Feito.** Mais proteção contra anúncios de animal, documento oficial, polícia, fumo e cosmético. |
| Palavras distintivas e nomes sugeridos dos tópicos | **Feito.** Os nomes são sugestão; o grupo decide. |
| Períodos de mesmo tamanho | **Feito**, no caderno `equilibrio_periodos.ipynb`. |
| Mudança por tipo | **Feito**, no caderno `mudanca_por_tipo.ipynb`. |
| Categorias (qualidades, defeitos, marcas no corpo, ofício e cor) | **Feito**, no caderno `categorias_por_periodo.ipynb`. O grupo ainda escolhe quais destacar. |
| Material do grupo | **Feito**, no caderno `material_do_grupo.ipynb`. |
| Resumo de uma página | **Feito**: `resumo_dados.md`, com os números lidos do banco. |
| Auditoria dos anúncios típicos | **Feita, meta não atingida.** Ver a seção do [plano_dados.md](plano_dados.md). |

### Os dados (24/11)

| | Hoje |
|---|---|
| Páginas capturadas | **158** (amostra principal 69 de 69, Diário do RJ e extras) |
| Páginas com anúncios separados | **109** (faltam 49) |
| Anúncios separados | 11.612 |
| Anúncios de pessoas escravizadas (campos `c4`) | **701**, e mais **67** `aluguel_incerto` fora do corpus |
| Corpus para o LDA (`corp2`) | **655** |

| Período | No corpus | Fuga | Venda | Aluguel | Ama de leite | Compra |
|---|---:|---:|---:|---:|---:|---:|
| antes de 1831 | 102 | 59 | 24 | 7 | 12 | 0 |
| 1831–1850 | 134 | 26 | 50 | 33 | 20 | 5 |
| 1850–1871 | 192 | 43 | 54 | 70 | 23 | 2 |
| 1871–1888 | 227 | 41 | 56 | 115 | 13 | 2 |
| **Total** | **655** | 169 | 184 | 225 | 68 | 9 |

Todos os períodos passam de 100 anúncios. Antes de 1831, quase todos os anúncios vêm do Diário do RJ (101 de 106 na rodada anterior).

### A ferramenta (`hdb`, 341 testes)

| Etapa | Comando | Situação |
|---|---|---|
| Contar e escolher termos | `hdb buscar`, `hdb acervos`, `hdb panorama` | pronto; 134 termos contados |
| Capturar página (CAPTCHA por pessoa) e OCR | `hdb capturar`, `scripts/amostra.py` | pronto; ~63 s por página |
| Separar anúncios | `hdb anuncios` (agora pula o que já foi feito; `--refazer`) | pronto, versão `v2` |
| Extrair campos | `hdb campos` | pronto, versão **`c5`** (antes `c4`) |
| Corpus padronizado | `hdb corpus` | pronto, versão **`corp3`** (antes `corp2`); variante `corp3i` para comparar |
| Modelagem de tópicos | `hdb topicos` | pronto; `t5` (k=6, corpus `corp3`) é a principal; `t5i` (sensibilidade) e `t4` (corpus antigo) gravados |
| Estabilidade do LDA | `scripts/estabilidade_topicos.py` | pronto |
| Relatório metodológico | `hdb relatorio` | pronto; seção de limites ampliada |
| Limpeza e conferência (Etapa 2) | `scripts/rodar_tudo.py`, `scripts/avaliar_limpeza.py` | pronto em 25/11 (versão `c5` na classificação) |

### O que cada versão corrigiu

| Versão | Problema que resolveu |
|---|---|
| `c3` | aluguel, venda e compra só com palavra de pessoa; sala, casa e "senhora portuguesa" saem |
| `c4` | aluguel só vale com marca de escravizado (preto, pardo, moleque…); "criada" e "rapariga" viram `aluguel_incerto`; o anúncio colado ao vizinho deixa de contaminar a regra. Em 10 aluguéis de 1871–1888 sorteados, **9 de 10 eram de pessoas escravizadas** (antes, cerca de 4). |
| `corp2` | erros de OCR unificados (`luga`→`aluga`, `recisa`→`precisa`); nomes próprios e loteria fora; `aluguel_incerto` fora |

### Os notebooks

| Notebook | O que mostra |
|---|---|
| [como_funciona.ipynb](notebooks/como_funciona.ipynb) | o caminho inteiro, do jornal ao anúncio |
| [analise_descritiva.ipynb](notebooks/analise_descritiva.ipynb) | tipo, sexo, idade, nação, recompensa e densidade por período |
| [topicos_por_periodo.ipynb](notebooks/topicos_por_periodo.ipynb) | os tópicos por período, sexo, idade e tipo |
| [equilibrio_periodos.ipynb](notebooks/equilibrio_periodos.ipynb) | os períodos com o mesmo número de anúncios |
| [mudanca_por_tipo.ipynb](notebooks/mudanca_por_tipo.ipynb) | palavras distintivas e atributos por tipo e período |
| [categorias_por_periodo.ipynb](notebooks/categorias_por_periodo.ipynb) | qualidades, defeitos, marcas, ofício e cor por período |
| [material_do_grupo.ipynb](notebooks/material_do_grupo.ipynb) | material para o grupo: aluguéis duvidosos, temas para nomear, trocas do OCR e conferência |

### Os resultados provisórios

**Estabilidade (10 sementes por k):** k=4 repete 58% dos tópicos; **k=6, 50%**; k=8, 43%; k=10, 37%; k=12, 34% (corpus de 2.094 anúncios, medido em 24/11). Usamos o **k=6** como principal e o k=8 como comparação.

**Temas que se repetem nas sementes (k=8):** fuga (0,95), serviço doméstico de mulheres (0,85), ama de leite (0,80) e aluguel de serviço (0,77). **Temas fracos:** um tópico geral de venda (0,64) e os dois tópicos pequenos e misturados do k=6 (avisos com lugar e data; venda de moleques e colunas variadas).

| O que os números mostram (`t4`, 2.094 anúncios) | antes de 1831 | 1831–50 | 1850–71 | 1871–88 |
|---|---:|---:|---:|---:|
| Tópico de aluguel de mulheres e ama de leite (T2) | 13,1% | 23,1% | 27,6% | **28,5%** |
| Tópico de fuga (T0) | **42,8%** | 18,6% | 15,1% | 15,5% |
| Fuga com recompensa (de 546 fugas) | 52% | 65% | 30% | 13% |

**Cuidado com a leitura:** a fuga é 58% dos anúncios antes de 1831 e 27% em 1871–1888 (19% em 1850–1871; o aumento vem das páginas de cobertura dos anos 1880). Parte da mudança vem do que as frases de busca acharam em cada período.

---

## Parte 2: O que falta

### A. Dados (mais urgente)

| # | Tarefa | Quem | Tempo | Depende de | Pronto quando |
|---|---|---|---|---|---|
| A1 | **Parcialmente feito.** As 33 páginas de JC 1827–1839 foram separadas só pelo texto (`v2t`). **Falta** as 16 páginas do JC dos anos 1860 (364568_05, várias colunas): `git pull`, depois `hdb palavras --subir` (envia o cache de `data/ocr_palavras/`, sem OCR novo), `hdb anuncios` e `hdb campos`, **sem apagar `data/amostra/`** | quem capturou essas páginas | ~1 h | as imagens ou o cache `data/ocr_palavras/` existirem na máquina dele | nenhuma página do JC dos anos 1860 com texto sem anúncios |
| A2 | **Cobrir 1886–1888**: listar mais páginas de `"escrav* fugid*"` no JC 1880s (hoje só há 1880, 1881 e 1885) e capturar uma amostra sorteada por ano. **Situação:** listagem de 1886–1888 em andamento; falta capturar com `--cobertura` | Diego (listar) e quem captura | listar ~1 h; capturar ~8 páginas, 2 CAPTCHAs | nada | existem anúncios dos anos 1886, 1887 e 1888 |
| A3 | **Complemento** (91 páginas, `--complemento`): 5 de 91 capturadas; extras 47 de 47. Os acervos DRJ 1860–78 e Correio Mercantil voltaram a responder | quem capturou | — | — | `scripts/amostra.py situacao` mostra o andamento |
| A4 | **FEITO: palavras do OCR no banco.** A captura já separa os anúncios e grava as palavras (tabela `paginas_palavras`). Se as imagens da A1 sumiram, `hdb palavras --subir` envia o cache que estiver em `data/ocr_palavras/`; sem esse cache, as páginas precisam ser recapturadas, com CAPTCHA | Claude implementa; grupo recaptura | — | — | `hdb anuncios` refaz a separação a partir do banco |

### B. Qualidade

| # | Tarefa | Quem | Pronto quando |
|---|---|---|---|
| B1 | **FEITO em 25/11 (automático; revisão de Claude, não do grupo).** Conferir 10 anúncios por período (15 min cada) e anotar erros de tipo, sexo e anúncios colados. Conferência com 120 + 40 anúncios sorteados, medida por `scripts/avaliar_limpeza.py`; o grupo pode repetir com os mesmos arquivos | as 3 pessoas | se o tipo estiver certo em 8 de 10, seguimos; senão, nova versão de `campos` |
| B2 | **FEITO em 25/11 como variante (`corp3i`, só para comparar).** Decidir o que fazer com os 67 `aluguel_incerto`: ficam de fora do corpus (hoje), entram como tipo à parte, ou entram só se tiverem cor. A escolha final continua com o grupo | grupo | decisão registrada no relatório |
| B3 | **FEITO em 25/11** (regras de tipo `c5` e motivo `sem_pessoa`). Filtrar o ruído que sobrou: avisos de navegação e juízo (tópico 5), banhos medicinais passando como fuga, colunas inteiras de classificados | Claude | os tópicos de ruído somem ou ficam isolados |
| B4 | **PARCIAL, 25/11:** o corte de anúncios colados está feito (`corp3`). Usar o travessão como divisor (separação v3) continua pendente | Claude | os anúncios do exemplo 5941 saem separados |
| B5 | **56 fragmentos** com menos de 60 caracteres | Claude | juntados ao anúncio vizinho ou descartados |
| B6 | **FEITO em 25/11:** erros de OCR da primeira letra (`luga`→`aluga`, `ozinha`→`cozinha`) corrigidos no corpus; as demais correções possíveis só são listadas | Claude | aplicado no `corp3` |

### C. Análise e apresentação (trabalho do grupo)

| # | Tarefa | Quem | Depende de |
|---|---|---|---|
| C1 | **FEITO em 24/11 com o corpus de 2.094 anúncios (sem as 49 páginas):** repetir a sequência: `hdb corpus`, `hdb topicos`, estabilidade, notebooks e relatório | Claude (~15 min) | A1 |
| C2 | **Nomear os tópicos.** Os nomes do notebook são só sugestão. Ler as palavras e uns 5 anúncios de cada um | as 3 pessoas | C1 |
| C3 | **Contextualização histórica** das leis do próprio período, com a dissertação indicada pela Fernanda | as 3 pessoas | — |
| C4 | **De 2 a 3 slides por período**: tópicos, exemplos de anúncios, contexto | as 3 pessoas | C2 e C3 |
| C5 | **Montar a apresentação** e gerar o relatório final (`hdb relatorio`) | Pessoa 1 | C4 |

### D. Documentação e organização

| # | Tarefa | Quem |
|---|---|---|
| D1 | **FEITO em 24/11.** Atualizar [guia_ferramenta.md](guia_ferramenta.md) e [linguagem_natural.md](linguagem_natural.md) com `corpus`, `topicos`, `c4`, `aluguel_incerto` e `--refazer` | Claude |
| D2 | **FEITO em 24/11.** Atualizar a tabela de situação do [README](README.md) e de [projeto.md](projeto.md) | Claude |
| D5 | **FEITO em 25/11.** Guia e linguagem natural atualizados com `c5`, `corp3`, `t5` e `t5i`, `rodar_tudo.py`, `avaliar_limpeza.py` e a repetição automática de consultas ao banco | Claude |
| D6 | **FEITO em 25/11.** Guia, linguagem natural, planejamento e plano de dados atualizados com o bloqueio do site, a segmentação pelo texto, os cadernos novos e o resumo | Claude |
| D3 | Tutorial de captura: a edição local do Diego (sem o passo do `.env`) ainda não foi commitada | Diego decide |
| D4 | Confirmar com o professor a data da apresentação | Diego |

### Ordem

```
A1 (outra máquina) ──► C1 (Claude) ──► C2 nomear ──► C4 slides ──► C5 apresentação
A2 (1886–1888) ─────────► C1 (nova rodada)           ▲
B1 (conferir 10) ──► B2 (decidir aluguel)           │
C3 (contexto histórico) ─────────────────────────────┘
```

A1 e B1 podem começar hoje, em paralelo. A2 é o que mais fortalece a conclusão.

---

## Parte 3: Melhorias possíveis

Em ordem de retorno para o projeto. Nenhuma é obrigatória.

### Para a conclusão ficar mais forte

| # | Melhoria | Por quê | Esforço |
|---|---|---|---|
| M1 | **Checagem de cobertura:** capturar ~10 páginas por período **sem termo de busca** e contar quantos anúncios de escravizados as frases perderam | é a melhor defesa contra a crítica "a amostra foi escolhida pelas frases"; exige um ajuste na captura | médio |
| M2 | **Buscar vendas e compras de homens depois de 1850** com palavras soltas na mesma página (`vende escravo`), porque a frase "vende-se um preto" some | a amostra de venda hoje tem viés para mulheres | médio |
| M3 | **Segundo jornal** (Correio Mercantil, Diário do RJ 1860–78) | mostra se o padrão é do jornal ou da época; a HDB tem falhado para esses acervos | depende do site |
| M4 | **FEITO** (`--equilibrar`, `--cobertura`). **Mais anúncios por período**, sorteando por ano em vez de seguir a ordem da lista | a cobertura de anos fica uniforme | baixo |

### Para os tópicos ficarem mais limpos

| # | Melhoria | Por quê | Esforço |
|---|---|---|---|
| M5 | **PARCIAL, 25/11:** palavras distintivas e atributos dentro de cada tipo (`mudanca_por_tipo.ipynb`). **Pendente:** um modelo de tópicos por tipo (só fuga, só aluguel…) além do geral | os tópicos hoje seguem em grande parte o tipo; dentro de cada tipo os temas mostram mudança real | baixo |
| M6 | **Expressões de duas palavras** ("ama de leite", "de nação", "bom cozinheiro") como uma unidade | o LDA separa palavras que só fazem sentido juntas | baixo |
| M7 | **Métrica de coerência** (c_v, com `gensim`) além da estabilidade | escolher o número de tópicos por mais de um critério | baixo |
| M8 | **Lista de grafias e de palavras vazias revisada pelo grupo** (Pessoas 2 e 3 do plano anterior). A primeira versão foi gerada pela ferramenta a partir das palavras mais frequentes | quem conhece o período acha o que a ferramenta não vê | baixo |
| M9 | **BERTopic** (modelo de linguagem) para comparar com o LDA | só se sobrar tempo; baixa um modelo grande | alto |

### Para a ferramenta

| # | Melhoria | Por quê | Esforço |
|---|---|---|---|
| M10 | **FEITO** (A4). **Guardar as palavras do OCR no banco** (atividade 3.1) | ninguém depende de imagens de outra máquina; permite melhorar a separação depois | médio |
| M11 | **Melhorar o OCR do JC 1860–1880** (pré-processamento da imagem; confiança média hoje em 63–67) | os anos 1870 têm "LUGA-SE", "cosinta", "engomms" | médio |
| M12 | **Extrair idade e valor em mais anúncios** (hoje só 13% têm idade; 3 fugas têm valor de recompensa) | os recortes por idade têm n de 9 a 58 | médio |
| M13 | **Regra de venda e compra com marca de escravizado**, como no aluguel (`c5`) | "VENDE-SE uma criada" ainda passa | baixo |
| M14 | **Tela para o grupo consultar tópicos e anúncios** (página simples lendo o banco) | quem não programa lê e confere sem SQL | médio |

---

## Os limites que precisam aparecer na apresentação

1. A amostra vem de **frases de busca**, não do jornal inteiro. As proporções (tipo, sexo) não representam o jornal.
2. **Antes de 1831** a amostra é quase toda do Diário do RJ; os outros períodos, do Jornal do Commercio.
3. O JC dos anos 1880 cobre 1880, 1881 e 1885, **e nada de 1886 a 1888**, que é o fim do período mais interessante.
4. Só 13% dos anúncios têm idade, e o sexo, dentro do mesmo tipo, quase não separa os tópicos.
5. O OCR dos anos 1860–1880 é pior; sobram palavras quebradas e anúncios colados.
6. **Os tópicos são padrões de palavras, não fatos.** Os nomes são hipóteses do grupo.
7. A queda da fuga e a subida do aluguel entre os períodos são em parte efeito da composição da amostra (ver M1, M2 e M4).
8. As páginas de 1827–1839 foram separadas só pelo texto do OCR (versão `v2t`), que é menos precisa que a separação pelas posições. A concordância entre as duas está em `scripts/validar_texto.py`.

---

## Riscos

| Risco | O que fazer |
|---|---|
| As imagens das 16 páginas do JC dos anos 1860 não existem mais | plano B (A4): guardar as palavras no banco e recapturar |
| O site da HDB bloqueia ou muda | amostra pequena, pausas fixas, nada repetido; avisar o Diego |
| Os acervos do Diário do RJ e do Correio Mercantil continuam a falhar | seguir só com o Jornal do Commercio |
| Poucos anúncios por período dão tópicos instáveis | rodar a estabilidade a cada mudança de corpus e usar k=6 |
| Os tópicos refletem o que as frases acharam, não o jornal | escrever isso nos slides; fazer a checagem de cobertura (M1) se der |
| O plano gratuito do Supabase enche | improvável; a Pessoa 1 acompanha |

---

## Quem faz o quê

| Pessoa | Período | Leis para contextualizar |
|---|---|---|
| **Pessoa 1** (ferramenta) | 1871–1888 | Ventre Livre (1871), Sexagenários (1885), Áurea (1888) |
| **Pessoa 2** | antes de 1831 e 1831–1850 | Lei Feijó (1831) |
| **Pessoa 3** | 1850–1871 | Lei Eusébio de Queirós (1850) |

Cada pessoa confere, nomeia os tópicos e apresenta o **próprio período**. A captura segue o [tutorial rápido](tutorial_captura.md). Regras fixas: o `.env` nunca é compartilhado em grupo; o CAPTCHA é sempre digitado por uma pessoa; nada de `data/` e `.env` vai para o git.
