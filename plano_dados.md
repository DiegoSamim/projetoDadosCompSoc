# Plano do trabalho com os dados

Situação em 25/11/2026. Este plano cobre só os **dados**: coleta, correções, melhorias e categorização. A ferramenta de linguagem natural e a apresentação ficam em [planejamento.md](planejamento.md).

## Quem faz o quê

| Quem | Faz |
|---|---|
| **Diego** | captura (digita o código de segurança), testes no site, decisões sobre os dados, leitura de anúncios |
| **Claude** | planeja e revisa; os ajustes no código são feitos por agentes e revisados antes de entrar; roda as análises de novo e atualiza cadernos e relatório |
| **Grupo** | confere anúncios por período, dá nome aos temas |

## Onde estamos

| O quê | Situação |
|---|---|
| Páginas lidas | 285 |
| Anúncios de pessoas escravizadas | 2.417 (2.094 entram na análise de temas) |
| Amostra principal e extras | completas |
| Complemento | 69 de 91 páginas |
| Anos 1887 e 1888 | **nenhuma página** |
| Ano de 1886 | só 13 anúncios |
| Páginas de 1827–1839 sem anúncios separados | 0 (separadas só pelo texto, `v2t`; 1.6) |
| Páginas do JC dos anos 1860 sem anúncios separados | 16 (esperam as imagens da outra máquina) |
| Site da Biblioteca Nacional | bloqueou nossos pedidos em 24/11 por excesso de acessos; desde 25/11 a ferramenta espera e para sem marcar erro (1.1) |

## Ordem geral

```
Etapa 1  Coleta ────────► Etapa 2  Correções ────────► Etapa 3  Melhorias
(1887–1888 e o que falta)  (lixo, colados, conferência)  (equilíbrio, recortes)
                                                               │
Etapa 5  Fechar os números ◄──── Etapa 4  Categorização ◄──────┘
(rodar tudo e congelar)          (nomes dos temas, categorias)
```

As etapas 1 e 2 podem andar juntas: enquanto se espera o site liberar, dá para corrigir os dados que já temos.

---

## Etapa 1. Coleta: juntar o que falta

### 1.1 Ensinar a ferramenta a respeitar o site (Claude) — FEITO em 25/11
Hoje, quando o site manda esperar, a ferramenta insiste, e cada página que falha gasta uma das 3 tentativas.
- A ferramenta passa a esperar sozinha quando o site pede pausa, aumenta o intervalo nas listagens longas e, se o bloqueio continuar, para com uma mensagem clara em vez de queimar tentativas.
- **Pronto quando:** os testes passam e uma simulação de bloqueio mostra a ferramenta parando sem marcar as páginas como erro.
- **Tempo:** ~1 h. Não depende do site.
- **Feito:** a espera segue o `Retry-After` do site (ou uma espera que dobra a cada bloqueio, com teto de 15 minutos). Depois de 3 respostas de bloqueio seguidas, a ferramenta para com a mensagem "tente de novo mais tarde" e código de saída 2. Na captura, a página que volta para a fila não ganha erro nem perde tentativa. Nas listagens longas, a pausa passa de 1,5 para 3 segundos depois de 200 passos. Há testes automáticos para a espera, a parada e a captura que não marca erro.

### Resultado da coleta rápida de 25/11 (itens 1.2 a 1.4)
**Feito em cerca de 30 minutos, só o essencial.** O site voltou; a lista de "escravo fugido" (1.121 ocorrências) levaria mais de 1 hora, então listamos **seis frases pequenas de fuga** no JC dos anos 1880 (73, 112, 33, 14, 7 e 3 ocorrências) e capturamos as de 1887 em diante.
- **1887 entrou:** 14 páginas capturadas, 33 anúncios de pessoas (6 de "fugio o escravo", 6 de "preto fugido", 2 de "fugio a escrava").
- **1888 continua sem nenhuma página.** Nas seis frases (245 ocorrências) o último ano é 1887. Uma busca por frases de 1888 ("lei áurea", "13 de maio de 1888") foi inconclusiva, porque a lista sai em ordem de data e só se vê o começo. **Não sabemos se 1888 está fora do acervo digitalizado ou se essas frases não ocorrem nele.** A Lei Áurea fica sem descrição direta.
- **Atenção:** os 33 anúncios de 1887 vêm só de frases de fuga; o resto de 1871–1888 tem aluguel e venda. O último período fica mais voltado à fuga.
- **Ferramenta:** a captura ganhou `--ano-min` (via `scripts/amostra.py`, constante `ANO_MIN_COBERTURA`), que tira da reserva as páginas de anos anteriores; a cobertura usa agora essas seis frases.
- **O complemento ficou em 69 de 91 páginas** (as 22 restantes são opcionais).

### 1.2 Ver se o site liberou (Diego)
- Abrir no navegador: https://memoria.bn.gov.br/docreader/docreader.aspx?bib=364568_07&Pesq=%22escravo%20fugido%22
- Se a página abrir, avisar o Claude. Se não abrir, esperar mais um dia.
- **Não** rodar captura nem listagem para testar.

### 1.3 Listar as páginas de 1887 e 1888 (Claude)
A lista de páginas do Jornal do Commercio dos anos 1880 parou em 942 de 1.121 por causa do bloqueio. As que faltam são justamente as do fim da década.
- Retomar a listagem de "escravo fugido" do ponto onde parou (~180 páginas, ~10 min com pausas).
- Se 1887–1888 tiver pouca coisa, listar também "escrava fugida" no mesmo jornal.
- Também listar **outros tipos** em 1885–1888 (venda, aluguel, ama de leite), para que o último período não fique só com fugas. As frases serão escolhidas pela contagem.
- **Pronto quando:** existe uma lista com páginas de 1887 e de 1888.

### 1.4 Capturar 1886–1888 (Diego)
- Rodar a captura de cobertura. Ela já escolhe uma página de cada ano por vez.
- Meta: **pelo menos 6 páginas de cada ano** (1886, 1887 e 1888), de fuga e dos outros tipos.
- **Tempo:** ~30 a 40 páginas, ~8 códigos de segurança, ~40 min.
- **Pronto quando:** a situação da cobertura mostra 1887 e 1888 na linha "anos ok".

### 1.5 Terminar o complemento (Diego)
Faltam 22 páginas, nesta ordem de prioridade:

| Prioridade | Frase | Jornal | Faltam | Por quê |
|---|---|---|---|---|
| 1 | "vende-se uma crioula" | JC 1860s | 3 | equilibra a venda de mulheres |
| 2 | "compra-se uma escrava" | JC 1850s | 4 | compra tem só 35 anúncios |
| 3 | "compra-se uma preta" | JC 1850s | 3 | idem |
| 4 | "escravo fugido" | Diário do Rio 1860–78 | 6 | **testar antes**; o site já respondeu "biblioteca não encontrada" |
| 5 | "escrav* fugid*" | Correio Mercantil | 6 | idem |

- Os itens 4 e 5: Claude faz **um único** pedido de teste em cada. Se falharem, saem do plano e isso entra no relatório como limite.
- **Pronto quando:** os itens 1 a 3 estão capturados, e os itens 4 e 5 estão capturados ou anotados como impossíveis.

### 1.6 Separar os anúncios das 33 páginas de 1827–1839 (outra máquina) — FEITO em 25/11, pelo texto, nos acervos 01 e 02
Essas páginas foram capturadas em outra máquina e o texto está no banco, mas os anúncios não foram separados.
- Na outra máquina: atualizar o código e enviar as palavras lidas (comandos no fim deste documento).
- **Feito:** Claude separou as páginas a partir do texto já guardado no banco, com um resultado um pouco pior (versão `v2t`, comando `hdb anuncios --do-texto --bib 364568_01 364568_02`). Foi aplicado só aos acervos 364568_01 e 364568_02, que têm poucas colunas e anúncios numerados.
- **Não entrou:** o JC dos anos 1860 (364568_05, várias colunas). Pelo texto, o programa mistura as colunas nele. Essas 16 páginas continuam esperando as imagens da outra máquina (comandos no fim deste documento).
- **Pronto quando:** os jornais 364568_01 e 364568_02 aparecem com anúncios na contagem por jornal. Atendido para 01 e 02; o 05 segue pendente.

---

## Etapa 2. Correções: limpar o que temos

**Feita em 25/11, de forma automática.** As cinco tarefas abaixo foram resolvidas por regras no código. A conferência é **revisão de Claude, não do grupo**. O grupo pode repetir a conferência com os arquivos `tests/fixtures/conferencia.json` e `tests/fixtures/conferencia_extra.json`, rodando `scripts/avaliar_limpeza.py`.

### Resultado da Etapa 2 (medido em 25/11)

| O que | Antes | Depois |
|---|---|---|
| Lixo que entrava no corpus (conferência de 120, rótulos de Claude) | 21 de 111 | **1** |
| Anúncios verdadeiros que a limpeza tira do corpus (mesma conferência) | 0 | **0** de 90 |
| Tipo certo (mesma conferência) | 96,7% | 96,7% |
| Segunda amostra de 40 (35 com rótulo): lixo / perdidos | 15 / 0 | 1 / 0 |
| Fugas no banco | 546 | 479 (67 viraram `outro`) |
| Anúncios no corpus | 2.094 | **2.012** |
| Fugas do corpus sem nenhuma palavra de pessoa (contagem de palavras) | 136 | 63 |

**Como ler esses números, sem exagero:**
- Os rótulos da conferência são de **Claude**, não do grupo. O grupo pode refazer com os mesmos arquivos (`scripts/avaliar_limpeza.py`).
- A **segunda amostra deixou de ser independente**: antes de ajustar, ela mostrou lixo 15 → 2 (bom), mas **3 de 20 anúncios verdadeiros perdidos** (fugas com "sabe ler", "natural de" ou "escravo" mal lido). Ajustei três regras para isso, então o resultado final dela está "viciado". O primeiro conjunto também foi usado para ajustar. **Números honestos de generalização são os da segunda amostra antes do ajuste:** lixo −87%, mas ~15% de perda nas fugas com OCR muito ruim.
- A meta "fugas sem pessoa ≤ 10" **não foi atingida** pela contagem de palavras (63). Mas uma leitura de 24 dos casos que sobram mostrou que cerca de 20 são fugas reais com OCR estragado ("vscravo", "eseras vo", "esorava"); só uns 3 ou 4 são lixo (loja de camisas, uma cautela, um anúncio de livro). Ou seja, o contador superestima o lixo.
- Dos 18 anúncios "mais típicos" lidos (3 por tópico), **3 têm problema** (uma fuga de africano livre, um anúncio de comércio marcado como ama de leite e um aluguel de homem agrupado com o serviço doméstico), acima da meta de 2 em 30.

**O que mudou de lado no caminho (vale registrar):**
1. A regra "fuga só com sinal de pessoa" **no corpus** era estrita demais no início (perdia 22 de 90 anúncios verdadeiros) e foi ampliada para idade, nação, "de nome", sinais do corpo e roupa levada.
2. A descoberta automática de erros de OCR aplicava **2.247 trocas**, muitas erradas ("alho → alto", "alianca → afianca"). Ficou restrita a **44 trocas** do tipo "perdeu a primeira letra" (luga → aluga, ozinha → cozinha); o resto só é listado.
3. O corpus **não removia** anúncios que deixaram de ser selecionados quando uma regra ficava mais rígida (só fazia upsert). Corrigido: regravar a mesma versão substitui de verdade.
4. Com uma semente fixa, **3 anúncios a mais reorganizaram todos os tópicos** (a estabilidade de k = 6 foi de 54% a 39% e voltou a 59%). O modelo agora usa a **semente mais representativa entre 10** (`--semente auto`), e os cadernos dão nome aos tópicos pelas palavras (o número muda a cada rodada).
5. Os cadernos avisam sozinhos quando o número de anúncios não é mais o que os comentários descrevem.

**Efeito nos temas:** o modelo novo (`t5`) separa melhor: o ruído que formava os dois tópicos fracos do modelo antigo sumiu (esses dois não têm par: cosseno 0,38 e 0,63). A direção do resultado se mantém **com e sem os 170 aluguéis duvidosos** (variante `t5i`): serviço doméstico sobe a cada período e a fuga cai de perto da metade para cerca de um quinto.

### 2.1 Tirar o lixo (Claude prepara, Diego decide)
**FEITO de forma automática em 25/11.** A classificação `c5` só marca fuga com sinal de pessoa; anúncios de animal, papel, remédio e relato de navio viram `outro`. Fuga sem sinal de pessoa fica fora do modelo (motivo `sem_pessoa`), mas continua no banco. Diego ainda pode revisar a lista de casos duvidosos.
Entraram textos que não são anúncios de pessoas: relatos de navios ("fugio para terra no escaler"), notícias (desastre na estrada de ferro), propaganda (banhos medicinais) e avisos de animais perdidos.
1. Claude monta regras para achar esses textos: palavras de navegação, notícia e comércio sem nenhuma palavra de pessoa, ou "fugio" sem escravo, preto, pardo etc.
2. Claude mostra a Diego **uma lista com os 50 casos mais duvidosos**, cada um com o texto e o motivo.
3. Diego marca quais são lixo e quais são anúncios de verdade. Claude ajusta as regras até errar pouco.
- **Pronto quando:** nos 30 anúncios mais típicos de cada tema, no máximo 2 são lixo. Hoje, em alguns temas, são 2 de 3.
- **Tempo:** Claude ~2 h; Diego ~30 min de leitura.

### 2.2 Anúncios colados (Claude)
**FEITO de forma automática em 25/11.** No corpus `corp3`, o corte (`cortar_colado`) fica com o primeiro trecho que tem pessoa quando há outra abertura colada; o texto original não muda. A conferência de 20 exemplos com Diego ainda pode ser feita.
Às vezes dois anúncios vizinhos ficam num pedaço só ("VENDE-SE uma casa... VENDE-SE um escravo").
1. Contar quantos pedaços têm mais de uma palavra de abertura (VENDE-SE, ALUGA-SE, FUGIO...) no meio do texto.
2. Cortar nesses pontos e conferir com Diego 20 exemplos antes e depois.
- **Pronto quando:** os pedaços com duas aberturas caem pela metade, sem cortar anúncios bons ao meio.

### 2.3 Conferir a classificação por amostra (grupo)
**FEITO de forma automática em 25/11.** A conferência foi feita por Claude, não pelo grupo: 120 anúncios sorteados (`tests/fixtures/conferencia.json`) e 40 numa segunda amostra (`conferencia_extra.json`), medidos por `scripts/avaliar_limpeza.py`. Metas do script: o ruído cai pelo menos 50% e os anúncios verdadeiros perdidos ficam em até 3%. O grupo pode repetir com os mesmos arquivos.
O computador marca tipo, sexo, idade, nação e recompensa por regras. Precisamos saber quanto ele erra.
- Claude sorteia **10 anúncios por período** (40 no total) e monta uma tabela para conferência no caderno, com o texto e o que o computador marcou.
- Cada pessoa confere os períodos dela e marca certo ou errado em cada campo.
- O resultado vira uma frase no relatório, por exemplo "o tipo está certo em 36 de 40".
- **Pronto quando:** os 40 anúncios estão conferidos e a taxa de acerto está anotada.
- **Tempo:** ~20 min por pessoa.

### 2.4 Decidir os 192 aluguéis duvidosos (Diego, com o grupo)
**FEITO como variante, em 25/11.** A versão `corp3i` inclui os `aluguel_incerto` só para comparar; o corpus principal (`corp3`) continua sem eles. A escolha final entre (a), (b) e (c) continua com o grupo.
São anúncios de aluguel em que o texto não diz se a pessoa era escravizada ("precisa-se de uma criada", "aluga-se uma ama"). Hoje eles ficam **fora** da análise.
- Claude separa 20 exemplos.
- O grupo lê e escolhe uma de três opções:
  - **(a)** deixar fora (é o que acontece hoje);
  - **(b)** pôr dentro com uma marca, para poder comparar com e sem;
  - **(c)** pôr dentro só os que tiverem alguma pista, como "preta" ou "parda".
- **Recomendação:** (b), porque permite mostrar na apresentação que a conclusão não muda, ou que muda.

### 2.5 Erros de leitura mais comuns (Claude)
**FEITO de forma automática em 25/11, em parte.** A rotina `descobrir_ocr` acha e aplica no corpus os erros de perda da primeira letra (`luga`→`aluga`, `ozinha`→`cozinha`). As demais correções possíveis só são listadas. A aprovação das duvidosas, como `ende`→`vende`, ainda é de Diego.
O programa que lê a imagem troca letras ("ende" em vez de "vende", "annos" em vez de "anos"). Já existe uma lista de correções.
- Claude junta as 100 palavras mais frequentes que não existem em português e propõe correções.
- Diego aprova as duvidosas, como "ende" → "vende", que hoje é só uma suposição.
- **Pronto quando:** a lista está revisada e aplicada.

---

## Auditoria dos anúncios típicos (25/11)

Para testar as regras onde elas mais pesam, Claude leu os anúncios mais típicos de cada tópico e rotulou cada um como certo ou com problema. Foram duas rodadas:

| Rodada | O que mostrou |
|---|---|
| 1ª | Serviu para ajustar as regras (as correções da Etapa 2). |
| 2ª | Anúncios que as regras ainda não tinham visto. Ainda há problemas de tipos variados, a chamada cauda longa: casos raros que escapam das regras. |

- **Meta:** no máximo 2 problemas em 30 anúncios. **Não foi atingida.** A limpeza melhorou, mas os temas ainda podem ter ruído.
- **O que isso significa:** a cauda longa deve aparecer como limite na análise e na apresentação. Novas correções devem vir do que a leitura de casos novos mostrar, para não ajustar as regras só aos casos já vistos.
- Os rótulos são de Claude, não do grupo. O grupo pode repetir a conferência com os arquivos da Etapa 2.3.

---

## Etapa 3. Melhorias: deixar a comparação justa

### 3.1 Equilibrar os períodos (Claude, decisão do Diego) — FEITO de forma automática em 25/11
Hoje há 102 anúncios antes de 1831, 460 em 1831–1850, 1.132 em 1850–1871 e 400 em 1871–1888. O período maior "puxa" os temas.
- Opção A: rodar os temas com um **sorteio do mesmo número** de anúncios por período (~400 cada).
- Opção B: manter todos, mas mostrar sempre as porcentagens dentro de cada período (é o que fazemos hoje).
- **Recomendação:** fazer as duas e mostrar que os temas principais aparecem nas duas.
- **Feito:** o caderno `equilibrio_periodos.ipynb` faz a opção A, com sorteio do mesmo número de anúncios por período, repetido e com a média. A opção B continua nos cadernos de tópicos. **Falta:** a leitura do grupo sobre se os temas principais aparecem nas duas.

### 3.2 Separar o efeito do tipo de anúncio (Claude) — FEITO de forma automática em 25/11
Os temas seguem muito o tipo (fuga, venda, aluguel). A busca achou proporções diferentes de cada tipo em cada período: a fuga em 1871–1888 subiu só porque capturamos mais fugas dos anos 1880.
- Mostrar a mudança dos temas **dentro de cada tipo**, por exemplo como mudam os anúncios de fuga entre os períodos.
- **Pronto quando:** o caderno de temas tem um gráfico por tipo.
- **Feito:** o caderno `mudanca_por_tipo.ipynb` mostra, dentro de cada tipo, as palavras distintivas e os atributos por período.

### 3.3 Subperíodo 1885–1888 (Claude, depende da 1.4)
Os Sexagenários (1885) e a Lei Áurea (1888) caem no mesmo período, 1871–1888.
- Com 1886–1888 capturados, separar 1885–1888 como recorte próprio, só para descrever, sem tirar conclusões fortes, porque serão poucos anúncios.

### 3.4 Conferir os anos fracos (Claude)
Alguns anos têm quase nada: 1872 com 8 anúncios, 1884 com 5 e 1883 com 9.
- Ver se vale capturar 2 ou 3 páginas a mais desses anos, junto com a 1.4.

---

## Etapa 4. Categorização: organizar o que os anúncios dizem

### 4.1 Nomear os temas (grupo)
Os nomes atuais são sugestões do Claude. Para cada tema:
1. ler as 12 palavras principais e 5 anúncios típicos (estão no caderno de temas);
2. escolher um nome curto e escrever uma frase do porquê.
- Fazer **depois** da Etapa 2, porque a limpeza muda os temas.

### 4.2 Categorias novas a partir do texto (Claude propõe, grupo escolhe) — FEITO de forma automática em 25/11, com a escolha ainda com o grupo
Coisas que os anúncios dizem e que podemos contar por período:

| Categoria | Exemplo no texto | Para que serve |
|---|---|---|
| **Ofício** | cozinheiro, lavadeira, costureira, pajem, sapateiro | o que se valorizava em cada período |
| **Marcas no corpo** | marcas de castigo, cicatrizes, "falta de dentes" | a violência registrada nos anúncios |
| **Qualidades e defeitos** | "fiel", "sem vícios", "fujão", "bêbado" | como as pessoas eram descritas para venda e aluguel |
| **Lugar** | rua, freguesia, fazenda, "para fora da cidade" | de onde e para onde |
| **Cor** | preto, pardo, crioulo, cabra | mudança no vocabulário |

- O grupo escolhe **2 ou 3** dessas categorias. Claude monta as listas de palavras e conta.
- **Feito:** o caderno `categorias_por_periodo.ipynb` cobre qualidades, defeitos, marcas no corpo, ofício e cor (módulo `src/hdb/categorias.py`). A categoria Lugar ficou de fora desta rodada. **Falta:** o grupo escolher as 2 ou 3 que vai destacar.
- **Pronto quando:** as categorias escolhidas estão no caderno descritivo, com gráfico por período.

### 4.3 Recortes por sexo, idade e nação (Claude)
Já existem, mas com poucos casos: só 326 anúncios têm idade e só 131 citam nação.
- Depois da coleta, refazer e marcar nos gráficos quando o número for pequeno demais para comparar.

---

## Etapa 5. Fechar os números (Claude)

Quando as etapas 1 a 4 terminarem:
1. Classificar de novo, montar o conjunto final de anúncios e rodar os temas e o teste de confiança.
2. Atualizar os dois cadernos e o relatório.
3. **Congelar** essa versão: os números da apresentação são esses e não mudam mais.
4. Escrever um resumo de uma página com os números finais, para quem vai fazer os slides.

- **Pronto quando:** a versão final está gravada e o resumo foi entregue ao grupo.

---

## Decisões que são suas

| # | Decisão | Quando |
|---|---|---|
| 1 | Quais textos são lixo (lista de 50) | Etapa 2.1 |
| 2 | O que fazer com os 192 aluguéis duvidosos | Etapa 2.4 |
| 3 | Aprovar as correções de leitura duvidosas | Etapa 2.5 |
| 4 | Sorteio igual por período ou não | Etapa 3.1 |
| 5 | Quais categorias novas contar | Etapa 4.2 |
| 6 | Quando congelar a versão final | Etapa 5 |

## Riscos

| Risco | O que fazer |
|---|---|
| O site continua bloqueado por dias | fazer as Etapas 2 a 4 com o que já temos; na apresentação, dizer que 1887–1888 ficou de fora |
| 1887–1888 tem poucos anúncios de escravizados (perto da abolição eles somem) | isso já é um resultado; mostrar a queda em vez de esconder |
| A limpeza tira anúncios bons | conferir sempre a lista de casos duvidosos antes de aplicar |
| Os temas mudam muito depois da limpeza | por isso nomear os temas só depois da Etapa 2 |

## Comandos (para consulta)

Ver o andamento (não acessa o site, pode rodar à vontade):

```bash
PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao --cobertura
PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao --complemento
```

Capturar (só depois da 1.2):

```bash
git pull
PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar --cobertura
PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar --complemento
```

Na outra máquina (só para as 16 páginas do JC dos anos 1860, 1.6):

```bash
git pull
PYTHONPATH=src .venv/bin/python -m hdb palavras --subir
```

Depois de capturar, rodar a sequência de análise de uma vez (campos, corpus, tópicos, estabilidade, relatório e cadernos):

```bash
PYTHONPATH=src .venv/bin/python scripts/rodar_tudo.py
```
