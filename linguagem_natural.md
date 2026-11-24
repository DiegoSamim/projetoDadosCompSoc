# A ferramenta de linguagem natural

Este documento explica, em passos simples, **como o computador vai "ler" os anúncios** e encontrar os temas que se repetem neles. É a parte final do projeto: a **modelagem de tópicos**.

- O que buscar: [termos_busca.md](termos_busca.md). Como usar a ferramenta: [guia_ferramenta.md](guia_ferramenta.md). O que falta: [planejamento.md](planejamento.md).
- Exemplo com dados reais, do jornal até a tabela de anúncios: [notebooks/como_funciona.ipynb](notebooks/como_funciona.ipynb).

## O que é "linguagem natural"

**Processamento de linguagem natural (PLN)** é o conjunto de técnicas para o computador trabalhar com texto escrito por pessoas, e não com números. No projeto, o PLN tem duas partes:

| Parte | O que faz | Como | Situação |
|---|---|---|---|
| **Regras** | Separa os anúncios e tira deles tipo, sexo, idade, nação, nome, recompensa | Listas de palavras e padrões ("de 14 a 16 annos", "de nação Benguella") | **Pronta** (`hdb anuncios`, `hdb campos`) |
| **Tópicos** | Acha **sozinha** os temas que se repetem nos anúncios, por período legal | Estatística sobre as palavras (LDA) ou um modelo de linguagem (BERTopic) | **Pronta** (`hdb corpus`, `hdb topicos`; LDA) |

A diferença: nas **regras**, nós dizemos ao computador o que procurar. Nos **tópicos**, o computador nos mostra padrões que talvez não esperássemos. Por exemplo, que anúncios de aluguel depois de 1850 falam muito de "cozinhar, lavar e engommar".

## Onde ela entra no caminho

```
Jornal (HDB) → imagem → OCR (texto) → anúncios → campos (regras)
                                                    ↓
                     1. escolher os anúncios (o corpus)
                     2. padronizar o texto
                     3. transformar texto em números
                     4. achar os tópicos (LDA / BERTopic)
                     5. ler e dar nome aos tópicos (o grupo)
                     6. comparar os tópicos entre os períodos legais
```

As etapas 1 a 4 são feitas pelo computador. As etapas 5 e 6 são trabalho de pesquisa do grupo.

## Passo a passo

### 1. Escolher os anúncios (o corpus)

**O quê:** separar, entre todos os anúncios do banco, só os que falam de pessoas escravizadas, e com texto legível.

**Como:** a view `anuncios_completos` já tem tudo o que é preciso. O critério proposto:

- tipo diferente de `outro` (fuga, venda, compra, aluguel, ama de leite);
- confiança do OCR acima de um mínimo (por exemplo 50);
- pelo menos umas 8 palavras (anúncios mais curtos são pedaços).

**Retorno:** uma tabela com um anúncio por linha: texto, ano, período legal, tipo, sexo. Hoje são 655 anúncios no corpus (campos `c4`, corpus `corp2`). Com a amostra do grupo capturada, a estimativa é de algumas centenas a mais.

### 2. Padronizar o texto

**Por quê:** para o computador, `hum`, `um` e `huma` são palavras diferentes, e `fugio` e `fugiu` também. Sem padronizar, o mesmo tema se espalha por várias grafias e some no meio do ruído.

**O que fazer, em ordem:**

1. tudo em minúsculas e sem acento;
2. grafia da época → grafia atual: `hum`→`um`, `huma`→`uma`, `annos`→`anos`, `fugio`→`fugiu`, `ph`→`f`, `camiza`→`camisa`, `Benguella`→`benguela`;
3. tirar números, endereços ("rua do Rozario n. 107") e pontuação;
4. tirar as **palavras vazias**: artigos, preposições e palavras que aparecem em todo anúncio (`de`, `a`, `o`, `que`, `na`, `se`, `rua`, `casa`, `trata`);
5. guardar o texto padronizado **ao lado** do original. O original nunca é apagado.

**Exemplo, com um anúncio real** (Jornal do Commercio, 1840):

> **Original:** FUGIO hum molecote de 14 a 16 annos de idade, de nação Benguella, de nome Joaquim, levando vestido camiza de baeta amarela e calças de lila preta, bastante relinto; adverte-se que fugio na sabbado 4 do corrente; quem do mesmo der noticias, dirijase ao largo do Paço n, 5.
>
> **Padronizado:** fugiu molecote anos idade nacao benguela nome joaquim levando vestido camisa baeta amarela calcas lila preta bastante fugiu sabado corrente noticias

Repare que `relinto` (um erro do OCR) sumiria ao filtrar palavras que não existem no vocabulário da época.

### 3. Transformar o texto em números

O computador não lê palavras: ele conta. Cada anúncio vira uma linha de contagens:

| anúncio | fugiu | molecote | benguela | leite | parto | engommar | alugar |
|---|---|---|---|---|---|---|---|
| fuga do Joaquim (1840) | 2 | 1 | 1 | 0 | 0 | 0 | 0 |
| "ALUGA-SE huma preta ama de leite do primeiro parto, que terá 19 annos" (1840) | 0 | 0 | 0 | 1 | 1 | 0 | 1 |

Para o **LDA** é isso: a "sacola de palavras" de cada anúncio. O **BERTopic** faz diferente: um modelo de linguagem lê a frase inteira e a transforma numa lista de números que representa o **sentido**. Assim, "fugio hum preto" e "desappareceu um escravo" ficam próximos mesmo sem palavras em comum.

### 4. Achar os tópicos

**O que é um tópico:** um grupo de palavras que costumam aparecer juntas. Cada anúncio é uma mistura de tópicos, por exemplo 70% de um e 30% de outro.

**Exemplo de como o resultado aparece.** É uma ilustração, não um resultado: os tópicos reais só existirão depois de rodar.

| Tópico | Palavras mais fortes | Nome que o grupo daria |
|---|---|---|
| 1 | fugiu, alvicaras, gratifica, cara, pes, signal, levou | Fuga e descrição do corpo |
| 2 | leite, parto, cria, sadia, primeiro, ama | Ama de leite |
| 3 | cozinhar, lavar, engommar, costurar, servico | Trabalho doméstico |
| 4 | nacao, benguela, mina, congo, cabinda, mocambique | Origem africana |

**As duas técnicas:**

| | LDA | BERTopic |
|---|---|---|
| Ideia | palavras que aparecem juntas formam um tópico | anúncios com sentido parecido formam um grupo |
| Bom em | ser rápido e fácil de explicar | textos curtos, como anúncios |
| Cuidado | precisa de texto bem padronizado; nós escolhemos o número de tópicos | baixa um modelo de linguagem (centenas de MB, uma vez); mais lento; o OCR ruim atrapalha |
| Ferramentas (gratuitas) | `scikit-learn` ou `gensim` | `bertopic` + `sentence-transformers` (modelo multilíngue ou BERTimbau) |

**Decisão do grupo:** usar o **LDA** (`scikit-learn`). Ele é gratuito e rápido, não precisa baixar modelo e é fácil de explicar na apresentação. Testar de 6 a 10 tópicos e escolher pela leitura, não só pela métrica. O BERTopic fica para o fim, só se sobrar tempo.

**Dois jeitos de comparar os períodos:**

- **um modelo para todos os anúncios** e depois medir quanto cada período usa cada tópico. **É o que vamos usar**, porque com poucos anúncios é o jeito mais estável;
- **um modelo por período legal**, mais fiel a cada época, mas instável quando o período tem poucos anúncios.

### 5. Ler e dar nome aos tópicos

O computador entrega listas de palavras e, para cada tópico, os anúncios mais típicos. O grupo:

- lê as palavras e uns 5 anúncios de cada tópico;
- dá um nome ("ama de leite", "fuga com recompensa");
- junta ou descarta tópicos sem sentido (às vezes um tópico é só lixo do OCR).

### 6. Comparar os períodos legais

Com os tópicos nomeados, medimos quanto cada um pesa em cada período. A tabela abaixo mostra **o formato** do resultado, sem números, que só existirão depois de rodar:

| Tópico | antes de 1831 | 1831–1850 | 1850–1871 | 1871–1888 |
|---|---|---|---|---|
| Fuga e descrição do corpo | … % | … % | … % | … % |
| Ama de leite | … % | … % | … % | … % |
| Origem africana | … % | … % | … % | … % |

**Perguntas que essa tabela responde:**

- os anúncios citam menos nações africanas depois do fim do tráfico (1850)?
- o aluguel e o trabalho doméstico crescem quando comprar fica caro?
- o que muda depois do Ventre Livre (1871)?

Os campos já extraídos (sexo, idade) permitem fazer o mesmo **por gênero e idade**, por exemplo os tópicos dos anúncios de mulheres comparados com os de homens. Era um dos pedidos da reunião.

## Como está na ferramenta

Segue o padrão dos outros comandos: tudo lido e gravado no banco, sem exportar arquivos.

| Comando | Entra | Sai |
|---|---|---|
| `hdb corpus` (versão `corp2`) | anúncios com campos (versão `c4`) | texto padronizado de cada anúncio, gravado ao lado do original |
| `hdb topicos --topicos 6 --versao t3` | o corpus | tópicos (palavras e pesos) e a mistura de tópicos de cada anúncio, gravados com o nome da versão |

- **Saída do `hdb corpus`:** quantos anúncios entraram no corpus e quantos foram descartados, com o motivo (tipo, aluguel sem marca de escravizado, OCR com confiança baixa, poucas palavras), e a contagem por período legal.
- **Saída do `hdb topicos`:** uma linha com o número de anúncios e a perplexidade. Depois, para cada tópico, quantos anúncios o têm como dominante, as palavras mais fortes e a divisão por período legal e por tipo.
- **Versões usadas:** `t3` (6 tópicos) é a principal; `t2` (8 tópicos) serve de comparação.

Depois, a análise (passos 5 e 6) é feita em um notebook, lendo o banco ([notebooks/topicos_por_periodo.ipynb](notebooks/topicos_por_periodo.ipynb)).

## Cuidados

- **Tópico não é fato histórico.** É um padrão de palavras. Quem dá sentido é a leitura do grupo, com a contextualização.
- **Poucos anúncios dão tópicos instáveis.** Com algumas centenas de anúncios, rode mais de uma vez e veja se os tópicos se repetem.
- **Estabilidade medida:** k=6 repete ~52% dos tópicos com similaridade ≥0,8; k=12, 21%. Por isso o k=6 é o principal, e o k=8 entra como comparação. Rode `scripts/estabilidade_topicos.py` a cada mudança no corpus.
- **O OCR deixa ruído.** Palavras erradas podem formar um "tópico de lixo". A padronização e o corte de confiança reduzem isso.
- **Anúncios grudados misturam temas.** Às vezes dois ou três anúncios vizinhos saem como um só. O jornal os separa com um travessão ("—"), e usar isso na separação é uma melhoria planejada.
- **A amostra não é sorteada do jornal inteiro.** Ela vem de frases de busca, então mostra os anúncios **que essas frases acham**. Vale dizer isso na apresentação; o relatório metodológico (`hdb relatorio`) registra o caminho.
