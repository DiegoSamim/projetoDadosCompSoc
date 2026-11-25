# Resumo dos dados

Gerado em 2026-11-25 a partir do banco. Versões: campos `c5`, corpus `corp3`, tópicos `t5`. Todos os números são lidos do banco.

## Anúncios por período e tipo

34.693 textos separados nas páginas, dos quais 2.560 são anúncios de pessoas (os demais, tipo `outro`, são casas, notícias, mercadorias etc.).

| Período | aluguel | venda | fuga | ama_de_leite | aluguel_incerto | compra | outro | Total |
|---|---|---|---|---|---|---|---|---|
| antes de 1831 | 18 | 43 | 80 | 26 | 1 | 0 | 645 | 813 |
| 1831–1850 | 163 | 211 | 123 | 73 | 17 | 19 | 2.348 | 2.954 |
| 1850–1871 | 520 | 295 | 212 | 111 | 90 | 19 | 14.334 | 15.581 |
| 1871–1888 | 201 | 89 | 125 | 30 | 89 | 5 | 14.806 | 15.345 |
| **Total** | 902 | 638 | 540 | 240 | 197 | 43 | 32.133 | 34.693 |

## Os temas e o peso de cada um por período

Proporção média do tema nos anúncios de cada período.

| Tema | Nome sugerido | Palavras principais | antes de 1831 (n = 152) | 1831–1850 (n = 565) | 1850–1871 (n = 1.085) | 1871–1888 (n = 389) |
|---|---|---|---|---|---|---|
| T0 | Aluguel de pretos e moleques para todo o serviço | aluga, preto, servico, todo, pretas | 5,3% | 13,4% | 18,2% | 17,0% |
| T1 | Fuga: nome, idade e dono | dia, nome, corrente, preto, fugiu | 14,9% | 9,4% | 8,6% | 9,8% |
| T2 | Venda com preço e qualidades | vende, preto, anos, bom, cozinheiro | 8,3% | 22,5% | 18,6% | 20,7% |
| T3 | Mulheres: lavar, engomar, cozinhar (aluguel e venda) | preta, aluga, lava, vende, lavar | 22,7% | 25,6% | 29,9% | 25,8% |
| T4 | Fuga: roupa levada e nação | nome, fugiu, dia, escravo, nacao | 31,4% | 14,7% | 11,9% | 15,4% |
| T5 | Ama de leite | leite, ama, aluga, boa, preta | 17,4% | 14,4% | 13,0% | 11,2% |

> **Ressalva:** os temas acompanham o tipo do anúncio (fuga, venda, aluguel, ama de leite): onde há mais anúncios de um tipo, o tema desse tipo pesa mais. Quando a mistura de tipos é igualada entre os períodos, os temas **não mostram mudança** (veja o caderno `robustez_mistura`); por isso esta tabela descreve a amostra e **não deve ser lida como uma tendência histórica**. Os nomes são sugestões, o grupo ainda os confirma.

## Quadro de afirmações

Nove afirmações fixadas antes de olhar os resultados. Cada uma compara o último período (1871–1888) com a base (o primeiro período com 30 anúncios ou mais), na visão bruta e só no Jornal do Commercio (e, nos temas, com a mistura de tipos igualada). **Sustentada** = a mudança é real em todas as visões; **parcial** = mesmo sentido, mas o intervalo inclui zero em alguma; **não sustentada** = o sentido muda ou contraria a frase; **frágil** = poucos anúncios. As afirmações 6 a 9 descrevem a amostra (mistura de tipos e temas), não achados históricos. Detalhes no caderno `afirmacoes`.

| # | Afirmação | Natureza | Base | Valor base → último (bruta) | Valor base → último (só JC) | Diferença [IC 95%] (bruta / só JC / ajustada) | p aj. | Forma | Veredito | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A recompensa nas fugas diminui | dentro do tipo | bruta: antes de 1831; só JC: 1831–1850 | 55,9 → 22,6 | 60,2 → 22,6 | -33,3 [-47,8; -19,0] / -37,6 [-50,7; -25,6] | <0,001 | um degrau | **sustentada** | Tendência bruta com p ajustado < 0,05 e diferença com intervalo sem zero, no mesmo sentido, em todas as visões. |
| 2 | A nação citada nas fugas diminui | dentro do tipo | bruta: antes de 1831; só JC: 1831–1850 | 52,9 → 2,2 | 45,4 → 2,2 | -50,8 [-63,2; -38,7] / -43,2 [-52,6; -34,1] | <0,001 | gradual | **sustentada** | Tendência bruta com p ajustado < 0,05 e diferença com intervalo sem zero, no mesmo sentido, em todas as visões. |
| 3 | As marcas no corpo nas fugas diminuem | dentro do tipo | bruta: antes de 1831; só JC: 1831–1850 | 48,5 → 17,2 | 21,3 → 17,2 | -31,3 [-45,6; -16,8] / -4,1 [-15,0; 6,8] | <0,001 | um degrau | **parcial** | Mesmo sinal em todas as visões, mas o intervalo da diferença contém zero na visão só JC. |
| 4 | A idade mediana dos fugidos aumenta | dentro do tipo | 1831–1850 | 21,5 → 30,0 | 21,5 → 30,0 | 8,5 [-0,2; 14,0] / 8,5 [-0,2; 14,0] anos | 0,007 | um degrau | **frágil** | Na visão bruta o último período tem menos de 30 anúncios (n ou n efetivo). |
| 5 | A parcela feminina dos aluguéis aumenta | dentro do tipo | 1831–1850 | 55,8 → 68,9 | 55,6 → 68,9 | 13,1 [2,8; 23,3] / 13,4 [2,4; 23,8] | 0,016 | gradual | **sustentada** | Tendência bruta com p ajustado < 0,05 e diferença com intervalo sem zero, no mesmo sentido, em todas as visões. |
| 6 | A fuga perde peso entre os anúncios | mistura da amostra | antes de 1831 | 44,7 → 23,9 | 28,8 → 23,9 | -20,8 [-29,9; -11,8] / -4,9 [-17,5; 7,6] | <0,001 | um degrau | **parcial** | Mesmo sinal em todas as visões, mas o intervalo da diferença contém zero na visão só JC. |
| 7 | Os temas de fuga perdem peso | tema (acompanha o tipo) | antes de 1831 | 46,3 → 25,2 | 31,7 → 25,2 | -21,1 [-28,9; -13,5] / -6,5 [-17,3; 4,4] / -2,6 [-10,3; 3,8] | 0,877 | um degrau | **não sustentada** | Igualando a mistura de tipos, o intervalo da diferença contém zero: a tendência bruta do tema é, em boa parte, mistura de tipos. |
| 8 | O serviço doméstico ganha peso | tema (acompanha o tipo) | antes de 1831 | 28,0 → 42,8 | 35,5 → 42,8 | 14,8 [8,4; 21,4] / 7,3 [-2,8; 17,0] / -6,4 [-15,1; 3,6] | <0,001 | um degrau | **não sustentada** | O sinal da diferença muda ou some na visão ajustada. |
| 9 | A ama de leite perde peso | tema (acompanha o tipo) | antes de 1831 | 17,4 → 11,2 | 22,4 → 11,2 | -6,1 [-11,1; -1,4] / -11,2 [-20,0; -2,7] / -3,2 [-8,2; 1,7] | <0,001 | gradual | **não sustentada** | Igualando a mistura de tipos, o intervalo da diferença contém zero: a tendência bruta do tema é, em boa parte, mistura de tipos. |

## Sinais principais

**Fuga com recompensa, por período.** O anúncio oferece recompensa (gratificação, alviçaras)?

| Período | Anúncios de fuga | Com recompensa |
|---|---|---|
| antes de 1831 | 80 | 52% |
| 1831–1850 | 123 | 59% |
| 1850–1871 | 212 | 30% |
| 1871–1888 | 125 | 17% |

_Ressalva: períodos com poucos anúncios variam muito; a amostra vem de frases de busca._

**Sexo, por tipo.** Feminino e masculino são % dos anúncios em que o sexo aparece.

| Tipo | Anúncios | Feminino | Masculino | Sexo não aparece |
|---|---|---|---|---|
| aluguel | 902 | 63% | 37% | 0% |
| venda | 638 | 48% | 52% | 0% |
| fuga | 540 | 19% | 81% | 24% |
| ama_de_leite | 240 | 98% | 2% | 1% |
| aluguel_incerto | 197 | 87% | 13% | 0% |
| compra | 43 | 43% | 57% | 0% |

_Ressalva: o sexo vem de palavras do texto; "ama de leite" é feminino por construção._

**Nação, por período.** As 3 mais citadas entre os anúncios que citam alguma nação.

| Período | Anúncios com nação | Mais citadas |
|---|---|---|
| antes de 1831 | 48 | Moçambique (29%), Benguela (23%), Cabinda (15%) |
| 1831–1850 | 67 | Cabinda (25%), Mina (22%), Moçambique (19%) |
| 1850–1871 | 44 | Angola (20%), Mina (16%), Benguela (16%) |
| 1871–1888 | 3 | Mina (67%), Congo (33%) |

_Ressalva: nação é o que o anunciante escreveu; muda de uso ao longo do século._

**Idade, por tipo.** Só dos anúncios que dizem a idade.

| Tipo | Com idade | Idade mediana (anos) |
|---|---|---|
| venda | 179 | 18,0 |
| fuga | 130 | 23,0 |
| aluguel | 31 | 16,0 |
| ama_de_leite | 26 | 19,0 |
| aluguel_incerto | 10 | 12,0 |
| compra | 3 | 7,0 |

_Ressalva: a idade é a que o anunciante disse (em geral aproximada)._

## Cobertura: onde temos páginas

| Jornal | Década | Páginas lidas | Anos presentes |
|---|---|---|---|
| Diário do Rio de Janeiro (RJ) - 1821 a 1858 | 1820s | 33 | 7 de 10: 1821–1822, 1824–1826, 1828–1829 |
| Diário do Rio de Janeiro (RJ) - 1821 a 1858 | 1830s | 2 | 2 de 10: 1831, 1836 |
| Imperio do Brasil: Diario Fluminense (RJ) - 1825 a 1831 | 1820s | 4 | 4 de 10: 1826–1829 |
| Imperio do Brasil: Diario Fluminense (RJ) - 1825 a 1831 | 1830s | 1 | 1 de 10: 1831 |
| Jornal do Commercio (RJ) - 1827 a 1829 | 1820s | 15 | 2 de 10: 1828–1829 |
| Jornal do Commercio (RJ) - 1830 a 1839 | 1830s | 18 | 7 de 10: 1830–1832, 1834–1836, 1838 |
| Jornal do Commercio (RJ) - 1840 a 1849 | 1840s | 30 | 10 de 10: 1840–1849 |
| Jornal do Commercio (RJ) - 1850 a 1859 | 1850s | 49 | 8 de 10: 1850–1856, 1859 |
| Jornal do Commercio (RJ) - 1860 a 1869 | 1860s | 51 | 10 de 10: 1860–1869 |
| Jornal do Commercio (RJ) - 1870 a 1879 | 1870s | 44 | 10 de 10: 1870–1879 |
| Jornal do Commercio (RJ) - 1880 a 1889 | 1880s | 52 | 8 de 10: 1880–1887 |

**Anos sem nenhuma página lida (1821–1888), 7 de 68:** 1823, 1833, 1837, 1839, 1857, 1858, **1888**.

## Os 3 limites principais

1. **Amostra por busca.** Os anúncios vêm de páginas achadas por frases de busca, não de sorteio: as proporções (tipo, sexo) descrevem o que a busca encontrou, não o jornal inteiro.
2. **Períodos desiguais.** Cada período tem outro número de anúncios, e antes de 1831 a amostra vem de outros jornais; parte da diferença entre períodos pode ser diferença de jornal ou de anos cobertos (ver o mapa de cobertura).
3. **Tópicos moderadamente estáveis.** Mudar a semente do sorteio ou alguns anúncios reorganiza os tópicos; os temas são pistas, e os nomes são hipóteses do grupo.
