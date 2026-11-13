# Projeto: Modelagem de Tópicos em Anúncios de Escravizados (HDB)

## Objetivos

O projeto usa modelagem de tópicos para identificar os temas recorrentes nos anúncios de pessoas escravizadas publicados em jornais brasileiros do século XIX. Também mostra como esses temas mudam entre os marcos legais que antecederam a abolição de 1888.

**Pergunta de pesquisa:** como o conteúdo dos anúncios de fuga, compra, venda, aluguel e ama de leite se transforma entre a Lei Feijó (1831) e a Lei Áurea (1888)?

**Objetivos específicos**

1. Extrair da Hemeroteca Digital Brasileira (HDB) as páginas com anúncios, a partir de frases de busca ("escravos fugidos", "vende-se uma preta", "aluga-se uma escrava", "preta com leite" etc.).
2. Obter o texto desses anúncios em formato que o computador consiga processar.
3. Dividir o corpus em períodos delimitados pelas leis Feijó (1831), Eusébio de Queirós (1850), do Ventre Livre (1871), dos Sexagenários (1885) e Áurea (1888).
4. Aplicar técnicas de processamento de linguagem natural (PLN) para extrair tópicos automaticamente, como amas de leite ou homens fugitivos, com recortes por gênero e idade quando possível.
5. Contextualizar historicamente os tópicos encontrados em cada período.

**Entregáveis finais**

- Tópicos gerados pela modelagem, por período.
- Pesquisa de contextualização histórica dos dados.
- Apresentação final em sala.

## Onde está cada coisa

| Documento | Para quê |
|---|---|
| [planejamento.md](planejamento.md) | O que já foi feito e o que falta, por fase |
| [termos_busca.md](termos_busca.md) | **O que vamos buscar** (a amostra do grupo) e as contagens que justificam a escolha |
| [guia_ferramenta.md](guia_ferramenta.md) | Como usar a ferramenta `hdb`, comando por comando |
| [linguagem_natural.md](linguagem_natural.md) | Como funciona a parte de linguagem natural: limpeza do texto e modelagem de tópicos |
| [notebooks/como_funciona.ipynb](notebooks/como_funciona.ipynb) | O caminho inteiro com dados reais, do jornal à tabela de anúncios |

## Etapas do projeto e situação

| Etapa | O que é | Situação |
|---|---|---|
| 1. Escolher o que buscar | Frases de busca por tipo de anúncio e período | **Feito.** 134 termos contados; amostra decidida (69 páginas novas, 5 tipos × 4 períodos) |
| 2. Obter o texto | Capturar a imagem da página e ler com OCR | **Funciona.** 39 páginas no banco; a amostra falta capturar |
| 3. Separar os anúncios | Dividir a página em colunas e anúncios | **Funciona.** 3.796 anúncios em 39 páginas |
| 4. Extrair campos | Tipo, sexo, idade, nação, nome, recompensa, período legal | **Funciona (heurístico).** 347 anúncios de pessoas escravizadas classificados |
| 5. Modelagem de tópicos | Limpar o texto e achar os temas por período | **A fazer.** Plano em [linguagem_natural.md](linguagem_natural.md) |
| 6. Contextualização e apresentação | Ler os tópicos à luz das leis e preparar a apresentação | A fazer, com o grupo |

## Desafios e como foram tratados

| Desafio | Situação |
|---|---|
| A HDB não entrega o texto das páginas (a exportação em PDF dá 404) | **Resolvido:** a ferramenta captura a imagem e faz o OCR localmente (Tesseract, gratuito) |
| A imagem da página pede CAPTCHA (desde 03/10/2025) | **Contornado sem burlar:** uma pessoa digita o código e a ferramenta faz o resto; cerca de 1 código por acervo aberto |
| O endereço antigo (`memoria.bn.br`) não existe mais, e a pyHDB não funciona como está | **Resolvido:** ferramenta própria no novo endereço (`memoria.bn.gov.br`), com as ideias da pyHDB (ver créditos no README) |
| Palavras soltas ("preto", "escravo") estão em quase todas as páginas | **Resolvido:** buscamos frases exatas, escolhidas pela contagem |
| As colunas do jornal se misturam no OCR | **Resolvido em boa parte:** separação por colunas e anúncios; às vezes dois anúncios vizinhos ainda ficam juntos |
| Não há tempo para transcrever ou rotular à mão | **Decidido:** nada é transcrito à mão; a conferência é feita por amostra, usando as evidências que a ferramenta grava |
| Ortografia da época ("hum", "fugio", "annos") e erros do OCR | **Em parte:** a extração de campos já tolera; a padronização para os tópicos está planejada |
| Capturar tudo levaria centenas de horas | **Decidido:** amostra pequena e variada (ver [termos_busca.md](termos_busca.md)) |

## Modelagem de tópicos

**Decisão:** LDA (`scikit-learn`), com um modelo para todos os anúncios. Os tópicos são depois comparados entre os períodos legais, e por sexo e idade. O BERTopic fica para o fim, só se sobrar tempo.

Quem faz o quê está em [planejamento.md](planejamento.md): 3 pessoas, cada uma com um ou dois períodos.

O passo a passo, com exemplos, está em [linguagem_natural.md](linguagem_natural.md).

## Decisões pendentes

- [ ] Confirmar com o professor a data da apresentação final.
- [ ] Definir quem é a Pessoa 1, a 2 e a 3 do [planejamento](planejamento.md).
- [ ] Receber a dissertação sobre anúncios de escravizados (Fernanda).

## Riscos

- **A BN pode bloquear coletas grandes.** Mitigação: amostra pequena, pausas fixas entre as ações e nada repetido (o banco lembra o que já foi feito).
- **A qualidade do OCR em jornais do século XIX pode ser baixa.** Mitigação: a confiança de cada página fica registrada, e os anúncios ilegíveis podem ser deixados de fora.
- **Poucos anúncios por período** podem dar tópicos instáveis. Mitigação: a amostra cobre os 4 períodos e os 5 tipos, e os tópicos são lidos e nomeados pelo grupo.
