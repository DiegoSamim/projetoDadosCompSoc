# Termos de busca na HDB: o que pesquisar e quantas páginas há

*Contagens de 10/11/2026, geradas por `scripts/contar_termos.py` (dados em `data/contagens_termos.csv`). Páginas por acervo: `scripts/contar_paginas.py`.*

Este documento serve para escolher **o que buscar** antes de capturar qualquer página. Cada número é a quantidade de **páginas** da Hemeroteca Digital Brasileira (HDB) em que a palavra ou frase aparece, num dos nove acervos pesquisados. Não é o número de anúncios: uma página pode ter vários anúncios, e uma página achada pode não ter nenhum anúncio de pessoa escravizada.

## O que vamos buscar (amostra do grupo)

**A decisão:** como não há tempo para milhares de páginas, vamos capturar **69 páginas novas, bem variadas**, além das 39 que já estão no banco. São **5 tipos de anúncio × 4 períodos legais**, e cada combinação é uma "célula" com seu termo e acervo. Uma página tem muitos anúncios (nas 39 de hoje saíram 347 anúncios de pessoas escravizadas, cerca de 9 por página), então a estimativa é de **algumas centenas de anúncios relevantes**, espalhados por todos os períodos e tipos.

| Período legal | Acervo | Fuga | Venda | Aluguel | Ama de leite | Compra |
|---|---|---|---|---|---|---|
| **antes de 1831** | JC 1827–29 (`364568_01`) | `"escravos fugidos"` · 4 | `"vende-se uma preta"` · 4 | `"aluga-se uma preta"` · 3 | `"preta com leite"` · 3 | `"compra-se escravos"` · 1 |
| **1831–1850** | JC 1830s (`364568_02`) | `"escravos fugidos"` · 4 | `"vende-se uma preta"` · 4 | `"aluga-se uma preta"` · 4 | `"preta com leite"` · 4 | `"compra-se um moleque"` · 2 |
| **1850–1871** | JC 1860s (`364568_05`) | `"fugio o escravo"` · 4 | `"vende-se uma preta"` · 4 | `"aluga-se uma escrava"` · 4 | `"preta com leite"` · 4 | `"compra-se escravos"` · 2 |
| **1871–1888** | JC 1870s (`364568_06`) | `"fugio o escravo"` · 4 | `"vende-se uma preta"` · 4 | `"aluga-se uma escrava"` · 4 | `"preta com leite"` · 4 | `"compra-se escravos"` · 2 |

O número depois do termo é quantas páginas capturar. As 39 páginas que já temos completam a tabela: Diário do RJ de 1821, Diário Fluminense de 1825–1831, Jornal do Commercio dos anos 1840, 1850, 1860 e 1880.

**Por que estas escolhas:**

- **Um jornal só, o Jornal do Commercio**, em quatro décadas. Assim a diferença entre períodos vem do tempo, e não da troca de jornal. É também o jornal com mais páginas em todas as décadas (ver o panorama do RJ 1850–1859).
- **Frases, não palavras soltas.** Cada frase acha páginas que quase certamente têm o anúncio do tipo certo. Palavras como `preto` aparecem em dois terços das páginas e não filtram nada.
- **A frase muda com a época.** Até 1850 o anúncio de fuga diz "escravos fugidos" ou "fugio um escravo". Depois, "fugio o escravo" e "escravo fugido". Por isso a fuga usa termos diferentes por período.
- **Poucas páginas por célula.** De 1 a 4. A compra é rara (de 1 a 15 páginas por acervo), por isso tem menos.
- **Variedade de graça.** Uma página achada por "vende-se uma preta" também traz aluguéis, fugas e anúncios de casas. A variedade não depende só do termo.
- **Sorteio.** A captura sorteia as páginas entre as listadas (`--aleatorio`), para não pegar só as primeiras edições.

**Limite conhecido:** a lista de ocorrências sai em ordem de data, e listamos no máximo 200 por célula. Nas células grandes ("escravos fugidos" nos 1830s tem 345 páginas, "compra-se escravos" nos 1860s tem 194), o sorteio fica nos primeiros anos da década. Para os objetivos do projeto isso é aceitável, porque comparamos períodos e não anos.

**Como rodar** (o plano está em `scripts/amostra.py`; tudo é retomável e não repete páginas). Cada pessoa usa `--pessoa 1`, `2` ou `3`, conforme a divisão do [planejamento](planejamento.md); sem `--pessoa`, o comando vale para a amostra inteira:

```bash
PYTHONPATH=src .venv/bin/python scripts/amostra.py situacao              # o que já foi feito, célula por célula
PYTHONPATH=src .venv/bin/python scripts/amostra.py listar --pessoa 2     # 1º: sem CAPTCHA, roda sozinho
PYTHONPATH=src .venv/bin/python scripts/amostra.py capturar --pessoa 2   # 2º: com uma pessoa para o CAPTCHA
```

**Quanto tempo leva, em estimativa:**

- **Listar:** cerca de 1.500 ocorrências a 3,6 s cada, ou 1,5 h, sem ninguém por perto.
- **Capturar:** de 1 a 2 h de computador para as 69 páginas. São 20 células, e o CAPTCHA aparece ao abrir cada uma, então são até 20 códigos para digitar.
- **Depois:** `hdb anuncios` e `hdb campos`, que rodam sozinhos (ver [guia_ferramenta.md](guia_ferramenta.md)).
- **Disco:** o script guarda as imagens em `data/amostra/`, porque `hdb anuncios` ainda precisa delas. São cerca de 6 MB por página, ou uns 400 MB para as 69.

O resto deste documento traz as contagens que embasaram a escolha.

## Resumo

- **Foram contados 134 termos e frases** em 9 acervos, que somam **181.594 páginas**: Jornal do Commercio (RJ) de 1827 a 1889 e Diário do Rio de Janeiro de 1821 a 1878.
- **Palavra solta não serve como filtro.** `preto` está em 64% das páginas do Jornal do Commercio nos anos 1840 a 1870, e `escravos` em 66% nos anos 1850 e 1860. Aparecem em muito mais do que anúncios de pessoas (provavelmente cor de roupa e de objetos, sobrenomes, notícias). `crioulo` e `moleque` estão em cerca de 29,0% e 28,4% das páginas dos anos 1850 e `negro`, em 7,5%: também amplos demais.
- **Frases coladas são muito mais específicas.** Para fuga, a busca `"escrav* fugid*"` reúne escravo, escrava, escravos e escravas fugido, fugida, fugidos e fugidas e encontra **11.062 páginas** (6,1% do total). É o melhor ponto de partida.
- **Venda, compra e aluguel têm, cada um, bem menos páginas que a fuga** (de 603 a 5.266 páginas por tipo, somando as frases, antes de tirar sobreposições). Capturar cada um por inteiro levaria de 7 h a 59 h (a 40 s por página), então também convém amostrar.
- **Amas de leite não se separam pela busca.** `"ama de leite"` aparece em 26.963 páginas, e a busca não separa mulheres livres de escravizadas. Juntar `preta` à busca não ajuda (ver "O que os números mostram"). Esse tipo vai depender da leitura do texto depois do OCR.
- **A grafia e a fórmula dos anúncios mudam com o tempo e de jornal para jornal.** É preciso buscar as duas grafias (`fugio` e `fugiu`) e esperar que frases que valem para os anos 1830 não valham para os 1860.

## Como a busca da HDB funciona

Testado em novembro de 2026 no próprio site.

| Regra | Exemplo |
|---|---|
| Não diferencia maiúscula nem acento | `nação` e `nacao`: 7.815 páginas nas duas |
| Aspas duplas buscam a **frase colada** | `"escravo fugido"`: 425 páginas (1850s) |
| Várias palavras **sem aspas** exigem todas na mesma página, em qualquer lugar | `escravo fugido`: 1.935 páginas (1850s) |
| O `*` no fim da palavra junta as variações | `escrav*`: 12.182 páginas; `escravo`: 8.424 (1850s) |
| O `*` também funciona dentro de uma frase | `"escrav* fugid*"` |
| **Não existe OU nem NÃO**: `preto OU preta` é lido como "as duas palavras" | `preto OU preta`: 7.384 páginas, menos que `preto` sozinho |
| Palavras muito comuns são ignoradas | `de`: 0 resultados |
| O hífen separa as palavras | `aluga-se` = `aluga se` = 3.859 páginas |
| Parte da grafia antiga é tratada como igual | `apprehender` ≈ `apreender`; `cativo` = `captivo` |
| Grafias diferentes de verbo **não** são tratadas como iguais | `fugiu`: 5 páginas e `fugio`: 53, no Diário Fluminense (1825–1831) |

Conferência: a HDB conta **páginas**. Nenhuma das 1206 contagens passa do total de páginas do seu acervo, e as 40 primeiras ocorrências de `preto` num acervo são 40 páginas diferentes.

## Acervos pesquisados

| Código | Jornal | Período | Páginas no acervo |
|---|---|---|---:|
| `364568_01` | Jornal do Commercio (RJ) | 1827–1829 | 2.638 |
| `364568_02` | Jornal do Commercio (RJ) | 1830–1839 | 12.120 |
| `364568_03` | Jornal do Commercio (RJ) | 1840–1849 | 14.871 |
| `364568_04` | Jornal do Commercio (RJ) | 1850–1859 | 15.569 |
| `364568_05` | Jornal do Commercio (RJ) | 1860–1869 | 16.704 |
| `364568_06` | Jornal do Commercio (RJ) | 1870–1879 | 23.266 |
| `364568_07` | Jornal do Commercio (RJ) | 1880–1889 | 24.285 |
| `094170_01` | Diário do Rio de Janeiro (RJ) | 1821–1858 | 46.933 |
| `094170_02` | Diário do Rio de Janeiro (RJ) | 1860–1878 | 25.208 |
| | **Total** | | **181.594** |

Os acervos do Diário do Rio de Janeiro cobrem 1821–1858 e 1860–1878. Como cada um agrupa muitos anos, não dá para separá-los pelos marcos legais de 1850 e 1871 só pela busca.

## O que pesquisar

### Por tipo de anúncio

Cada tipo tem várias frases, porque a pessoa anunciada aparece com palavras diferentes (escravo, preto, crioulo, pardo, moleque). As páginas se **sobrepõem**: a mesma página pode ser achada por mais de uma frase. Por isso a tabela dá os dois extremos, e o número real fica entre eles.

| Tipo de anúncio | Consultas | Páginas (maior consulta) | Páginas (soma bruta) | Jornal do Commercio | Diário do RJ |
|---|---:|---:|---:|---:|---:|
| Fuga | 17 | 11.062 | 16.436 | 10.911 | 5.525 |
| Venda | 13 | 2.250 | 4.803 | 2.004 | 2.799 |
| Compra | 8 | 445 | 603 | 436 | 167 |
| Aluguel | 11 | 3.813 | 5.266 | 3.240 | 2.026 |
| Ama de leite ("preta/escrava/crioula com leite") | 3 | 484 | 592 | 313 | 279 |
| Nações africanas (qualquer tipo) | 5 | 3.505 | 8.887 | 4.656 | 4.231 |

### Fuga: quanto custa capturar

Considerando só a busca `"escrav* fugid*"` e os marcos legais do projeto. Estimativas de tempo medidas em 33 páginas capturadas: mediana de 35 a 57 s por página no Jornal do Commercio (123 s nos anos 1880) e 6 s no Diário do RJ, quase tudo de OCR; usei 40 s por página. A listagem leva 3,6 s por página.

| Período (Jornal do Commercio) | Páginas com `"escrav* fugid*"` | % das páginas | Listar (sem CAPTCHA) | Capturar (40 s/pág.) |
|---|---:|---:|---:|---:|
| 1827–1849 (até Eusébio de Queirós) | 889 | 3,0% | 53 min | 10 h |
| 1850–1870 (Eusébio → Ventre Livre) | 1.872 | 5,8% | 2 h | 21 h |
| 1871–1888 (Ventre Livre → Áurea) | 3.989 | 8,4% | 4 h | 44 h |
| **Jornal do Commercio, tudo** | **6.750** | 6,2% | 7 h | 75 h |
| Diário do Rio de Janeiro, tudo (1821–1878) | 4.312 | 6,0% | 4 h | 48 h |

Capturar tudo seria trabalho de dezenas a centenas de horas. Por isso a recomendação é **amostrar**: sortear, dentro de cada período, algumas centenas de páginas dessa busca (por exemplo 150 por período, 450 páginas, cerca de 5 horas de captura). O CAPTCHA, nas 33 páginas capturadas, foi pedido 6 vezes, sempre ao abrir um acervo e não a cada página; falta confirmar isso numa captura mais longa.

### Ordem sugerida

1. **Fuga com curinga**: `"escrav* fugid*"` e `"fugi* o escrav*"`, nos dois jornais. Listar primeiro (sem CAPTCHA), depois sortear a amostra por período.
2. **Fuga com outras palavras de época**: `"preto fugido"`, `"preta fugida"`, `"pardo fugido"`, `"fugio o preto"`, `"fugio o crioulo"`, `"fugio o pardo"`.
3. **Venda, compra e aluguel**: por inteiro seriam dezenas de horas de captura, então também convém amostrar (4.803 páginas somando as vendas, 5.266 as de aluguel e 603 as de compra, antes de tirar as sobreposições). Começar por `"vende-se uma preta"`, `"aluga-se uma preta"` e `"compra-se escravos"`.
4. **Nações africanas** (`boçal`, `ladino`, `monjolo`, `rebolo`, `nagô`): provavelmente páginas de anúncios de pessoas, de qualquer tipo (expectativa, a conferir).
5. **Ama de leite**: capturar `"preta com leite"` e `"escrava com leite"` (poucas páginas) e uma amostra de `"ama de leite"`; separar livres e escravizadas pelo texto, depois do OCR.
6. **Palavras soltas e o grupo "liberdade e lei"** não são para capturar páginas: servem para filtrar o texto depois do OCR e para ver onde cada lei aparece.

## O que os números mostram

- **A grafia muda por jornal.** No Jornal do Commercio, `fugio` aparece em 21.604 páginas e `fugiu` em 1.330, e o `fugio` continua forte até os anos 1880 (3.084 contra 103). No Diário do Rio de Janeiro de 1860–1878, a relação se inverte: `fugiu` (776) passa `fugio` (618).
- **A fórmula do anúncio de fuga muda por volta de 1850.** `"fugio um escravo"` (o verbo) aparece em 26 páginas nos anos 1830, em 7 nos 1840 e em nenhuma depois; `"escravo fugido"` (o particípio) vai de 31 nos 1840 para 425 nos 1850 e 1.410 nos 1870.
- **O anúncio de venda parece mudar de palavras.** No Jornal do Commercio, `"vende-se um escravo"` some depois dos anos 1840 (44 páginas nos 1830, 2 nos 1840, nenhuma depois), enquanto `"vende-se uma preta"` chega a 356 nos 1850. As vendas de homens com essas frases também somem (`"vende-se um preto"`, `"vende-se um moleque"`: nenhuma página nos 1850 em diante). Isso mais provavelmente indica **outra redação** do anúncio do que o fim das vendas, e só se confirma lendo amostras.
- **Aluguel pesa mais que venda.** `"aluga-se uma preta"` (3.813 páginas) passa `"vende-se uma preta"` (2.250).
- **Os marcos legais aparecem nos números**, o que confere a qualidade da contagem. No Jornal do Commercio: `ingenuo` vai de 122 páginas nos anos 1860 para 1.013 nos 1870 (Lei do Ventre Livre, 1871); `"fundo de emancipação"` vai de 2 para 326 e 1.307; `sexagenario` sobe de 36 para 104 nos anos 1880 (Lei dos Sexagenários, 1885).
- **A recompensa fica mais comum.** `gratifica` está em 0,2% das páginas do Jornal do Commercio em 1827–1829 e em 4,5% nos anos 1870.
- **Ama de leite.** `"ama de leite"` está em 27,1% das páginas do Jornal do Commercio dos anos 1850. `"ama de leite" preta` dá 25.258 páginas contra 26.963 da frase sozinha, ou seja, juntar `preta` quase não filtra. `"ama secca"` explode nos anos 1880 (3.436 páginas, contra 355 nos 1850).
- **"escravos fugidos" no Diário do RJ** tem 3.149 páginas em 1821–1858, contra 107 de `"escravo fugido"`. A diferença é grande demais para ser anúncio avulso, e é o **título de uma seção fixa** do jornal: conferi em 6 páginas de 1821 (acervo `094170_01`), onde "ESCRAVOS FUGIDOS." abre uma lista de avisos numerados ("34. A John Scurr fugirão… dous moleques Cabindas", "35. …dezapareceu huma negra inda boçal de Nação Cabinda"). Em 1821, portanto, uma só página dá dezenas de avisos de fuga. Não foi conferido nos outros anos do acervo (1822–1858).

## Tabelas completas

Colunas: os nove acervos, o total de páginas (soma dos acervos), a porcentagem do total de 181.594 páginas e a **precisão esperada** para anúncios de pessoas escravizadas. A precisão é uma **expectativa baseada no significado da palavra**, ainda não medida; ela só será conferida lendo uma amostra. Termos em ordem decrescente de páginas dentro de cada grupo. JC = Jornal do Commercio, DRJ = Diário do Rio de Janeiro.

### Curingas (`*`)

O `*` no fim da palavra junta gênero e número numa busca só. É o jeito mais curto de pegar as frases de fuga.

| Termo | JC 27–29 | JC 30s | JC 40s | JC 50s | JC 60s | JC 70s | JC 80s | DRJ 21–58 | DRJ 60–78 | Total | % das páginas | Precisão esperada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `escrav*` | 1.130 | 6.463 | 9.170 | 12.182 | 13.943 | 16.684 | 15.826 | 31.388 | 16.310 | **123.096** | 67,8% | baixa (inclui escravidão, escravizar etc.) |
| `negr*` | 399 | 2.545 | 4.429 | 5.587 | 6.563 | 8.364 | 8.137 | 9.734 | 6.125 | **51.883** | 28,6% | baixa |
| `fugid*` | 383 | 2.751 | 4.235 | 5.463 | 7.123 | 8.070 | 5.753 | 11.451 | 4.605 | **49.834** | 27,4% | baixa (também fuga de presos, animais) |
| `gratific*` | 154 | 2.148 | 4.353 | 6.378 | 7.227 | 8.482 | 7.710 | 9.039 | 3.382 | **48.873** | 26,9% | baixa (gratificação de funcionários) |
| `crioul*` | 240 | 2.202 | 3.413 | 5.927 | 7.765 | 8.558 | 5.149 | 11.441 | 2.213 | **46.908** | 25,8% | média (quase sempre pessoas) |
| `"escrav* fugid*"` | 208 | 397 | 284 | 671 | 1.201 | 2.113 | 1.876 | 3.464 | 848 | **11.062** | 6,1% | alta (pega escravo/escrava/escravos/escravas fugido/a/os/as) |
| `"fugi* o escrav*"` | 4 | 10 | 77 | 146 | 339 | 516 | 523 | 272 | 95 | **1.982** | 1,1% | alta (fugio/fugiu o escravo/a escrava) |

### Fuga

Frases de anúncio de fuga. A forma muda com o tempo: antes de 1850 predomina o verbo ("fugio um escravo"); depois, o particípio ("escravo fugido").

| Termo | JC 27–29 | JC 30s | JC 40s | JC 50s | JC 60s | JC 70s | JC 80s | DRJ 21–58 | DRJ 60–78 | Total | % das páginas | Precisão esperada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `fugio` | 271 | 2.195 | 3.593 | 3.954 | 4.004 | 4.503 | 3.084 | 8.523 | 618 | **30.745** | 16,9% | baixa (também "fugio o respeito", batalhas) |
| `fugido` | 54 | 417 | 724 | 2.304 | 4.003 | 4.748 | 2.869 | 2.623 | 2.971 | **20.713** | 11,4% | baixa |
| `fugidos` | 207 | 563 | 339 | 426 | 648 | 770 | 790 | 4.881 | 944 | **9.568** | 5,3% | baixa |
| `fugida` | 17 | 122 | 220 | 506 | 1.238 | 2.005 | 1.441 | 807 | 1.093 | **7.449** | 4,1% | baixa |
| `"escravos fugidos"` | 167 | 345 | 227 | 162 | 192 | 374 | 447 | 3.149 | 241 | **5.304** | 2,9% | alta? (no DRJ parece título de seção fixa: conferir) |
| `"escravo fugido"` | 19 | 29 | 31 | 425 | 814 | 1.410 | 1.121 | 107 | 465 | **4.421** | 2,4% | alta |
| `fugiu` | 7 | 114 | 294 | 331 | 201 | 280 | 103 | 1.027 | 776 | **3.133** | 1,7% | baixa |
| `"escrava fugida"` | 0 | 4 | 7 | 53 | 148 | 408 | 444 | 30 | 135 | **1.229** | 0,7% | alta |
| `"preto fugido"` | 1 | 9 | 21 | 184 | 212 | 339 | 112 | 44 | 16 | **938** | 0,5% | alta |
| `"fugio o preto"` | 1 | 7 | 88 | 103 | 68 | 87 | 14 | 265 | 2 | **635** | 0,3% | alta |
| `"preta fugida"` | 0 | 1 | 2 | 38 | 75 | 213 | 181 | 17 | 5 | **532** | 0,3% | alta |
| `"fugio o escravo"` | 0 | 1 | 54 | 76 | 101 | 111 | 73 | 105 | 7 | **528** | 0,3% | alta |
| `"fugio um escravo"` | 9 | 26 | 7 | 0 | 0 | 0 | 0 | 179 | 0 | **221** | 0,1% | alta |
| `"fugio a preta"` | 2 | 1 | 1 | 14 | 25 | 69 | 26 | 64 | 1 | **203** | 0,1% | alta |
| `"escravo fugio"` | 2 | 2 | 6 | 32 | 37 | 39 | 33 | 45 | 3 | **199** | 0,1% | alta |
| `"fugio o pardo"` | 0 | 0 | 11 | 35 | 32 | 37 | 6 | 29 | 3 | **153** | <0,1% | alta |
| `"pardo fugido"` | 0 | 0 | 2 | 39 | 35 | 45 | 18 | 4 | 6 | **149** | <0,1% | alta |
| `"fugio o crioulo"` | 0 | 0 | 11 | 20 | 26 | 19 | 2 | 51 | 2 | **131** | <0,1% | alta |
| `"fugio uma escrava"` | 0 | 7 | 7 | 5 | 2 | 3 | 3 | 72 | 0 | **99** | <0,1% | alta |
| `"fugio a escrava"` | 0 | 0 | 0 | 6 | 15 | 33 | 33 | 9 | 0 | **96** | <0,1% | alta |
| `"fugiu o escravo"` | 0 | 0 | 3 | 3 | 1 | 14 | 7 | 8 | 12 | **48** | <0,1% | alta |
| `"crioulo fugido"` | 0 | 4 | 0 | 4 | 7 | 10 | 4 | 12 | 1 | **42** | <0,1% | alta |
| `"negro fugido"` | 0 | 4 | 1 | 2 | 6 | 2 | 7 | 7 | 5 | **34** | <0,1% | alta |
| `"escrava fugio"` | 0 | 1 | 0 | 3 | 3 | 11 | 7 | 5 | 0 | **30** | <0,1% | alta |
| `"escravo fugiu"` | 0 | 1 | 0 | 0 | 4 | 0 | 1 | 6 | 2 | **14** | <0,1% | alta |
| `"crioula fugida"` | 0 | 0 | 0 | 3 | 1 | 2 | 6 | 0 | 0 | **12** | <0,1% | alta |
| `"fugiu a escrava"` | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 1 | 3 | **10** | <0,1% | alta |
| `"negra fugida"` | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | **4** | <0,1% | alta |
| `"fugiu uma escrava"` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | **2** | <0,1% | alta |
| `"escrava fugiu"` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | **2** | <0,1% | alta |
| `"fugiu um escravo"` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **1** | <0,1% | alta |
| `"fugio o negro"` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | **1** | <0,1% | alta |

### Recompensa e captura

Quase todo anúncio de fuga oferece recompensa, mas a mesma fórmula serve para objetos e animais perdidos.

| Termo | JC 27–29 | JC 30s | JC 40s | JC 50s | JC 60s | JC 70s | JC 80s | DRJ 21–58 | DRJ 60–78 | Total | % das páginas | Precisão esperada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `gratificação` | 65 | 1.156 | 2.208 | 3.295 | 3.180 | 3.416 | 2.675 | 4.479 | 1.822 | **22.296** | 12,3% | baixa |
| `"quem o levar"` | 32 | 892 | 2.366 | 2.850 | 2.812 | 2.729 | 1.957 | 3.884 | 270 | **17.792** | 9,8% | baixa (inclui objetos perdidos) |
| `apprehender` | 2 | 355 | 1.368 | 2.082 | 2.561 | 2.795 | 1.916 | 2.196 | 424 | **13.699** | 7,5% | baixa (a HDB trata como "apreender"; apreensões da polícia) |
| `"quem o apprehender"` | 2 | 226 | 1.055 | 1.647 | 1.926 | 2.094 | 1.394 | 1.628 | 285 | **10.257** | 5,6% | média (inclui objetos e animais) |
| `gratifica` | 4 | 27 | 93 | 381 | 734 | 1.049 | 772 | 182 | 62 | **3.304** | 1,8% | média (também objetos e animais perdidos) |
| `calabouço` | 19 | 210 | 164 | 176 | 159 | 73 | 41 | 1.035 | 154 | **2.031** | 1,1% | média (prisão de escravos no Rio) |
| `apprehendido` | 0 | 106 | 205 | 210 | 140 | 116 | 308 | 423 | 198 | **1.706** | 0,9% | baixa |
| `"quem o pegar"` | 23 | 206 | 137 | 18 | 9 | 5 | 6 | 1.174 | 6 | **1.584** | 0,9% | média |
| `"recolher a cadeia"` | 0 | 6 | 5 | 8 | 19 | 21 | 38 | 25 | 33 | **155** | <0,1% | alta |

### Descrição da pessoa

Origem ("nação") e sinais físicos. Os termos de nação são os mais específicos de anúncios de pessoas escravizadas.

| Termo | JC 27–29 | JC 30s | JC 40s | JC 50s | JC 60s | JC 70s | JC 80s | DRJ 21–58 | DRJ 60–78 | Total | % das páginas | Precisão esperada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `"de nação"` | 833 | 6.167 | 9.131 | 7.815 | 7.526 | 7.424 | 6.186 | 22.375 | 7.371 | **74.828** | 41,2% | baixa (também "de nação portuguesa") |
| `signaes` | 133 | 357 | 2.618 | 2.944 | 2.688 | 2.577 | 2.482 | 8.012 | 2.003 | **23.814** | 13,1% | baixa (também sinais de navios) |
| `fula` | 35 | 382 | 700 | 1.451 | 1.937 | 2.152 | 1.463 | 1.198 | 288 | **9.606** | 5,3% | média (cor de pele) |
| `congo` | 77 | 693 | 987 | 1.256 | 815 | 615 | 1.420 | 3.192 | 293 | **9.348** | 5,1% | média (também lugar) |
| `cabinda` | 225 | 657 | 1.008 | 971 | 736 | 355 | 150 | 3.843 | 198 | **8.143** | 4,5% | média |
| `ladino` | 137 | 360 | 365 | 210 | 204 | 268 | 143 | 1.769 | 49 | **3.505** | 1,9% | alta |
| `boçal` | 32 | 160 | 60 | 73 | 79 | 105 | 172 | 1.395 | 171 | **2.247** | 1,2% | alta (africano recém-chegado) |
| `cicatrizes` | 6 | 86 | 157 | 230 | 209 | 192 | 247 | 418 | 107 | **1.652** | 0,9% | média |
| `monjolo` | 15 | 181 | 285 | 192 | 170 | 175 | 77 | 276 | 37 | **1.408** | 0,8% | alta |
| `benguela` | 74 | 718 | 159 | 69 | 73 | 36 | 9 | 149 | 44 | **1.331** | 0,7% | média (nação, mas também lugar) |
| `rebolo` | 5 | 177 | 131 | 80 | 87 | 106 | 121 | 164 | 57 | **928** | 0,5% | alta |
| `nagô` | 6 | 53 | 93 | 121 | 94 | 69 | 50 | 281 | 32 | **799** | 0,4% | alta |

### Compra, venda e aluguel

Anúncios de comércio e de trabalho.

| Termo | JC 27–29 | JC 30s | JC 40s | JC 50s | JC 60s | JC 70s | JC 80s | DRJ 21–58 | DRJ 60–78 | Total | % das páginas | Precisão esperada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `"ama de leite"` | 171 | 1.503 | 3.159 | 4.221 | 3.668 | 4.289 | 4.085 | 5.643 | 224 | **26.963** | 14,8% | média (livres e escravizadas) |
| `"ama de leite" preta` | 124 | 1.401 | 3.062 | 4.118 | 3.577 | 4.104 | 3.523 | 5.212 | 137 | **25.258** | 13,9% | baixa (quase igual a "ama de leite": juntar as palavras não filtra) |
| `"ama de leite" escrava` | 52 | 681 | 1.697 | 2.649 | 2.941 | 3.206 | 2.637 | 2.663 | 54 | **16.580** | 9,1% | baixa (idem) |
| `"ama de leite" crioula` | 29 | 363 | 874 | 2.127 | 2.850 | 2.755 | 1.575 | 1.615 | 26 | **12.214** | 6,7% | baixa (idem) |
| `"ama secca"` | 0 | 10 | 100 | 355 | 822 | 1.478 | 3.436 | 142 | 76 | **6.419** | 3,5% | baixa (serviço doméstico, em geral livre) |
| `"amas de leite"` | 100 | 339 | 364 | 152 | 118 | 182 | 522 | 2.727 | 107 | **4.611** | 2,5% | média |
| `"aluga-se uma preta"` | 6 | 106 | 617 | 853 | 612 | 239 | 79 | 1.294 | 7 | **3.813** | 2,1% | alta |
| `"vende-se uma preta"` | 15 | 136 | 331 | 356 | 173 | 74 | 15 | 1.142 | 8 | **2.250** | 1,2% | alta |
| `"vende-se um preto"` | 9 | 110 | 36 | 0 | 0 | 0 | 0 | 575 | 0 | **730** | 0,4% | alta |
| `"aluga-se uma parda"` | 0 | 9 | 75 | 105 | 67 | 28 | 18 | 204 | 2 | **508** | 0,3% | alta |
| `"preta com leite"` | 9 | 50 | 53 | 24 | 37 | 39 | 19 | 252 | 1 | **484** | 0,3% | alta |
| `"compra-se escravos"` | 1 | 5 | 15 | 57 | 194 | 58 | 23 | 67 | 25 | **445** | 0,2% | alta |
| `"aluga-se uma escrava"` | 0 | 8 | 46 | 59 | 64 | 27 | 20 | 146 | 0 | **370** | 0,2% | alta |
| `"vende-se uma escrava"` | 6 | 28 | 39 | 34 | 23 | 12 | 3 | 203 | 0 | **348** | 0,2% | alta |
| `"vende-se uma parda"` | 0 | 25 | 44 | 62 | 30 | 19 | 3 | 114 | 2 | **299** | 0,2% | alta |
| `"vende-se um moleque"` | 4 | 53 | 20 | 0 | 0 | 0 | 0 | 203 | 0 | **280** | 0,2% | alta |
| `"vendem-se escravos"` | 8 | 44 | 35 | 23 | 12 | 7 | 3 | 132 | 2 | **266** | 0,1% | alta |
| `"aluga-se um preto"` | 0 | 47 | 8 | 0 | 0 | 0 | 0 | 205 | 0 | **260** | 0,1% | alta |
| `"aluga-se uma crioula"` | 0 | 9 | 13 | 27 | 35 | 14 | 13 | 116 | 0 | **227** | 0,1% | alta |
| `"vende-se um escravo"` | 2 | 44 | 2 | 0 | 0 | 0 | 0 | 177 | 0 | **225** | 0,1% | alta |
| `"vende-se uma crioula"` | 2 | 9 | 3 | 27 | 31 | 18 | 7 | 77 | 0 | **174** | <0,1% | alta |
| `"vende-se um pardo"` | 0 | 20 | 3 | 0 | 0 | 0 | 0 | 68 | 0 | **91** | <0,1% | alta |
| `"vendem-se pretos"` | 0 | 6 | 4 | 7 | 4 | 7 | 0 | 52 | 0 | **80** | <0,1% | alta |
| `"compra-se uma preta"` | 0 | 1 | 6 | 11 | 10 | 8 | 1 | 34 | 0 | **71** | <0,1% | alta |
| `"escrava com leite"` | 1 | 0 | 2 | 5 | 9 | 15 | 7 | 19 | 0 | **58** | <0,1% | alta |
| `"crioula com leite"` | 0 | 3 | 2 | 3 | 15 | 16 | 4 | 6 | 1 | **50** | <0,1% | alta |
| `"vende-se um crioulo"` | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 39 | 0 | **47** | <0,1% | alta |
| `"compra-se uma escrava"` | 0 | 0 | 5 | 10 | 3 | 8 | 4 | 12 | 2 | **44** | <0,1% | alta |
| `"aluga-se um moleque"` | 0 | 9 | 4 | 0 | 0 | 0 | 0 | 28 | 0 | **41** | <0,1% | alta |
| `"aluga-se um escravo"` | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 21 | 0 | **25** | <0,1% | alta |
| `"escravo de ganho"` | 0 | 0 | 0 | 6 | 6 | 2 | 0 | 0 | 0 | **14** | <0,1% | alta |
| `"compra-se um preto"` | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 11 | 0 | **14** | <0,1% | alta |
| `"compra-se um escravo"` | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | **11** | <0,1% | alta |
| `"compra-se um moleque"` | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 5 | 0 | **11** | <0,1% | alta |
| `"vende-se uma negra"` | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | **8** | <0,1% | alta |
| `"compram-se escravos"` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | **5** | <0,1% | alta |
| `"preta de ganho"` | 0 | 2 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | **5** | <0,1% | alta |
| `"vende-se um negro"` | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | **5** | <0,1% | alta |
| `"alugam-se escravos"` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | **3** | <0,1% | alta |
| `"compra-se uma crioula"` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | **2** | <0,1% | alta |
| `"alugam-se pretas"` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0,0% | alta |

### Palavras soltas

Muito frequentes e pouco específicas sozinhas: servem para filtrar o texto depois do OCR, não para escolher páginas.

| Termo | JC 27–29 | JC 30s | JC 40s | JC 50s | JC 60s | JC 70s | JC 80s | DRJ 21–58 | DRJ 60–78 | Total | % das páginas | Precisão esperada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `preto` | 667 | 5.369 | 9.447 | 9.906 | 11.329 | 14.971 | 14.130 | 23.633 | 10.648 | **100.100** | 55,1% | baixa |
| `escravos` | 818 | 5.149 | 7.385 | 10.310 | 11.052 | 10.507 | 8.873 | 23.120 | 12.456 | **89.670** | 49,4% | baixa |
| `preta` | 656 | 4.221 | 6.321 | 8.415 | 9.859 | 13.744 | 12.217 | 22.047 | 8.251 | **85.731** | 47,2% | baixa |
| `pretos` | 298 | 2.404 | 4.048 | 5.489 | 5.655 | 5.651 | 3.924 | 9.585 | 3.859 | **40.913** | 22,5% | baixa |
| `pardo` | 155 | 1.645 | 3.136 | 4.785 | 5.848 | 8.003 | 5.781 | 7.217 | 3.479 | **40.049** | 22,1% | baixa |
| `parda` | 128 | 1.465 | 3.088 | 4.687 | 5.433 | 7.651 | 6.538 | 7.704 | 2.018 | **38.712** | 21,3% | baixa |
| `pretas` | 273 | 1.835 | 3.867 | 5.095 | 5.324 | 6.546 | 4.430 | 7.739 | 3.409 | **38.518** | 21,2% | baixa |
| `moleque` | 378 | 2.683 | 4.200 | 4.421 | 4.070 | 4.750 | 3.124 | 10.140 | 710 | **34.476** | 19,0% | média |
| `crioulo` | 132 | 1.333 | 2.344 | 4.522 | 5.625 | 5.533 | 2.943 | 6.983 | 1.400 | **30.815** | 17,0% | baixa |
| `crioula` | 101 | 979 | 1.428 | 3.091 | 4.991 | 5.418 | 2.965 | 5.200 | 796 | **24.969** | 13,7% | baixa |
| `escravas` | 131 | 651 | 856 | 1.284 | 2.032 | 2.798 | 2.133 | 3.337 | 1.314 | **14.536** | 8,0% | baixa |
| `africano` | 13 | 160 | 679 | 1.502 | 2.019 | 1.988 | 2.064 | 1.646 | 3.437 | **13.508** | 7,4% | baixa |
| `negro` | 142 | 527 | 790 | 1.175 | 1.127 | 2.065 | 2.509 | 1.755 | 1.991 | **12.081** | 6,7% | baixa |
| `africana` | 6 | 196 | 310 | 675 | 1.247 | 1.668 | 1.721 | 548 | 2.469 | **8.840** | 4,9% | baixa |
| `negra` | 105 | 390 | 452 | 553 | 1.023 | 1.301 | 1.318 | 1.216 | 1.429 | **7.787** | 4,3% | baixa |
| `negros` | 72 | 383 | 668 | 602 | 483 | 655 | 797 | 1.101 | 1.141 | **5.902** | 3,3% | baixa |
| `molecote` | 18 | 454 | 469 | 704 | 763 | 681 | 258 | 925 | 177 | **4.449** | 2,4% | média |
| `cativo` | 10 | 178 | 645 | 424 | 377 | 397 | 447 | 511 | 217 | **3.206** | 1,8% | média (a HDB trata "cativo" e "captivo" como a mesma palavra) |
| `captivo` | 10 | 178 | 645 | 424 | 377 | 397 | 447 | 511 | 217 | **3.206** | 1,8% | baixa |
| `negras` | 29 | 127 | 214 | 259 | 294 | 454 | 398 | 433 | 520 | **2.728** | 1,5% | baixa |
| `crioulos` | 1 | 85 | 118 | 297 | 501 | 375 | 152 | 328 | 126 | **1.983** | 1,1% | baixa |
| `mulata` | 15 | 23 | 12 | 42 | 109 | 97 | 83 | 71 | 263 | **715** | 0,4% | baixa |
| `mulato` | 28 | 32 | 30 | 45 | 78 | 79 | 125 | 101 | 104 | **622** | 0,3% | baixa |

### Liberdade e lei (contexto)

Não são anúncios, mas mostram onde cada marco legal aparece no jornal.

| Termo | JC 27–29 | JC 30s | JC 40s | JC 50s | JC 60s | JC 70s | JC 80s | DRJ 21–58 | DRJ 60–78 | Total | % das páginas | Precisão esperada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `forro` | 238 | 1.208 | 1.999 | 3.760 | 4.656 | 4.627 | 3.736 | 5.784 | 3.263 | **29.271** | 16,1% | contexto (não é anúncio de pessoa) |
| `tráfico` | 126 | 441 | 739 | 1.143 | 519 | 478 | 677 | 1.547 | 486 | **6.156** | 3,4% | contexto (não é anúncio de pessoa) |
| `liberto` | 3 | 162 | 159 | 247 | 459 | 825 | 1.405 | 493 | 710 | **4.463** | 2,5% | contexto (não é anúncio de pessoa) |
| `contrabando` | 11 | 185 | 621 | 505 | 313 | 476 | 619 | 634 | 519 | **3.883** | 2,1% | contexto (não é anúncio de pessoa) |
| `ingenuo` | 0 | 14 | 96 | 95 | 122 | 1.013 | 1.186 | 137 | 640 | **3.303** | 1,8% | contexto (não é anúncio de pessoa) |
| `"fundo de emancipação"` | 0 | 0 | 0 | 0 | 2 | 326 | 1.307 | 0 | 259 | **1.894** | 1,0% | contexto (não é anúncio de pessoa) |
| `alforria` | 0 | 34 | 71 | 53 | 89 | 339 | 880 | 120 | 220 | **1.806** | 1,0% | contexto (não é anúncio de pessoa) |
| `"carta de liberdade"` | 1 | 17 | 26 | 49 | 102 | 315 | 422 | 69 | 153 | **1.154** | 0,6% | contexto (não é anúncio de pessoa) |
| `"ventre livre"` | 0 | 1 | 5 | 6 | 28 | 138 | 84 | 6 | 161 | **429** | 0,2% | contexto (não é anúncio de pessoa) |
| `sexagenario` | 0 | 0 | 16 | 16 | 33 | 36 | 104 | 25 | 50 | **280** | 0,2% | contexto (não é anúncio de pessoa) |

## Limites

- **Página não é anúncio.** Uma página tem vários anúncios, e o termo pode estar em qualquer um (ou numa notícia). O número de anúncios só vem depois do OCR e da separação dos anúncios.
- **A HDB só acha o que o OCR dela leu.** Se a palavra foi lida errado ("fugio" virou "lugio", como vimos), a página não é encontrada. Não sabemos quantas páginas relevantes ficam de fora.
- **As frases dependem da redação.** Uma frase que sumiu num período pode ter sido escrita de outro jeito (ver "O anúncio de venda parece mudar de palavras"). Convém testar variações com curinga, por exemplo `"vend* um escrav*"`.
- **Não some os números de linhas diferentes**: as páginas se repetem entre termos. A união só se conhece depois de listar as páginas.
- **A precisão esperada não foi medida.** A medição vem com a amostra de páginas lidas.
- **Só dois jornais do Rio de Janeiro.** Outras províncias e outros jornais ficam para depois.
- **Os acervos estão sendo reabertos pela BN**: os totais podem mudar. O tempo de captura (40 s por página) é a mediana de 33 páginas: varia de 6 s (Diário do RJ) a 123 s (Jornal do Commercio, anos 1880) e pode cair com mais processos de OCR.

## Como atualizar

```bash
# acrescentar termos em TERMOS (scripts/contar_termos.py) e rodar; só conta o que falta
PYTHONPATH=src python scripts/contar_termos.py
PYTHONPATH=src python scripts/contar_termos.py --categoria fuga   # só um grupo
PYTHONPATH=src python scripts/contar_paginas.py                   # total de páginas de cada acervo
```

As consultas são leves (uma requisição por termo e acervo, com 1,5 s de pausa) e não precisam de CAPTCHA.
