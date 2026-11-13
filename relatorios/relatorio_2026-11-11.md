# Relatório metodológico da coleta

Gerado em 11/11/2026 21:56. Fonte: Hemeroteca Digital Brasileira, https://memoria.bn.gov.br.

## 1. Regras da busca da HDB

- A HDB devolve **páginas**, não anúncios: cada ocorrência é uma página em que o termo aparece.
- A busca é por **palavra exata** (ignora maiúsculas e acentos); `*` no fim da palavra aceita variações.
- Aspas duplas buscam a **frase exata**; sem aspas, várias palavras devem estar na mesma página.
- Não há operadores OU nem NÃO.
- Palavras muito comuns (como `de`) são ignoradas pela HDB e devolvem 0 resultados.

## 2. Como o corpus foi formado

Para cada termo e acervo: quantas ocorrências a HDB informa, quantas foram listadas por nós e quantas páginas já foram capturadas.

| Termo | Acervo (bib) | Nome | No servidor | Listadas | Capturadas | Com erro | 1ª coleta | Última coleta |
|---|---|---|---|---|---|---|---|---|
| `"aluga-se uma preta"` | 364568_04 | Jornal do Commercio (RJ) - 1850 a 1859 | 853 | 3 | 3 | 0 | 11/11/2026 06:36 | 11/11/2026 06:36 |
| `"escrav* fugid*"` | 094170_01 | Diário do Rio de Janeiro (RJ) - 1821 a 1858 | 3.464 | 6 | 6 | 0 | 11/11/2026 06:35 | 11/11/2026 06:35 |
| `"escrav* fugid*"` | 364568_03 | Jornal do Commercio (RJ) - 1840 a 1849 | 284 | 6 | 6 | 0 | 11/11/2026 06:34 | 11/11/2026 06:34 |
| `"escrav* fugid*"` | 364568_05 | Jornal do Commercio (RJ) - 1860 a 1869 | 1.201 | 6 | 6 | 0 | 11/11/2026 06:34 | 11/11/2026 06:34 |
| `"escrav* fugid*"` | 364568_07 | Jornal do Commercio (RJ) - 1880 a 1889 | 1.876 | 6 | 6 | 0 | 11/11/2026 06:35 | 11/11/2026 06:35 |
| `"preta com leite"` | 364568_03 | Jornal do Commercio (RJ) - 1840 a 1849 | 53 | 3 | 3 | 0 | 11/11/2026 06:36 | 11/11/2026 06:36 |
| `"vende-se uma preta"` | 364568_04 | Jornal do Commercio (RJ) - 1850 a 1859 | 356 | 3 | 3 | 0 | 11/11/2026 06:36 | 11/11/2026 06:36 |
| `fugido` | 364568_04 | Jornal do Commercio (RJ) - 1850 a 1859 | 2.304 | 1 | 1 | 0 | 10/11/2026 15:15 | 10/11/2026 15:15 |
| `fugiu` | 706744 | Imperio do Brasil: Diario Fluminense (RJ) - 1825 a 1831 | 5 | 5 | 5 | 0 | 10/11/2026 15:09 | 10/11/2026 15:09 |

## 3. Captura

Uma pessoa resolve cada CAPTCHA; a ferramenta não o contorna. Total: 39 páginas ok, 6 CAPTCHAs (6,5 páginas por CAPTCHA).

| Quem | Páginas ok | CAPTCHAs | Erros por etapa | Segundos médios | Período |
|---|---|---|---|---|---|
| diego | 38 | 6 | ocr: 1 | 43,7 | 10/11/2026 15:09 a 11/11/2026 06:56 |
| reprocessar-cinza | 1 | 0 | – | 58,3 | 11/11/2026 13:42 a 11/11/2026 13:42 |

## 4. Texto (OCR)

| Motor | Páginas | Confiança média |
|---|---|---|
| tesseract-5.3.4 por psm3-pagina | 38 | 66,5 |
| tesseract-5.3.4 por psm3-pagina-cinza | 39 | 73,7 |

| Acervo (bib) | Nome | Páginas | Confiança média (leitura atual) |
|---|---|---|---|
| 094170_01 | Diário do Rio de Janeiro (RJ) - 1821 a 1858 | 6 | 79,6 |
| 364568_03 | Jornal do Commercio (RJ) - 1840 a 1849 | 9 | 84,4 |
| 364568_04 | Jornal do Commercio (RJ) - 1850 a 1859 | 7 | 70,5 |
| 364568_05 | Jornal do Commercio (RJ) - 1860 a 1869 | 6 | 56,5 |
| 364568_07 | Jornal do Commercio (RJ) - 1880 a 1889 | 6 | 65,5 |
| 706744 | Imperio do Brasil: Diario Fluminense (RJ) - 1825 a 1831 | 5 | 82,6 |

## 5. Anúncios e campos

| Versão da separação | Anúncios | Largos (cruzam colunas) | Páginas |
|---|---|---|---|
| v1 | 3.958 | 159 | 39 |
| v2 | 3.796 | 51 | 39 |

### Campos, versão c1

3.796 anúncios.

- Tipo: outro: 3.448, aluguel: 112, fuga: 102, venda: 90, ama_de_leite: 38, compra: 6
- Sexo: (sem sexo): 3.139, m: 341, f: 244, ambos: 72
- Com idade: 114; com nome: 52; com recompensa: 79
- Nações mais comuns: Mina (20), Angola (12), Benguela (8), Cabinda (7), Congo (6), Moçambique (5), Monjolo (3), Ganguela (2), Rebolo (2), Ambaca (1)

## 6. Panorama de acervos

| Local | Período | Periódicos na lista | Com código (bib) | Com erro |
|---|---|---|---|---|
| RJ | 1850 - 1859 | 66 | 66 | 0 |

_Nada registrado ainda._

## 7. Limites conhecidos

- O OCR erra letras (e às vezes palavras inteiras); a confiança é a média do Tesseract, não uma medida de acerto.
- A separação em anúncios e a extração de campos (tipo, sexo, idade, nação etc.) são heurísticas, sem revisão manual.
- A HDB conta **páginas** com o termo, não anúncios nem ocorrências dentro da página.
- As contagens do panorama valem para o **acervo inteiro**, não só para a década pedida; acervos que cobrem mais de uma década aparecem sinalizados.
- Não há rótulos manuais: nenhum campo foi conferido por pessoas, então não há taxa de acerto medida.

## 8. Créditos

- pyHDB (Eric Brasil, licença MIT): BRASIL, Eric. pyHDB – Ferramenta Heurística para a Hemeroteca Digital Brasileira. *História da Historiografia*, v. 15, n. 40, p. 186–217, 2022. DOI 10.15848/hh.v15i40.1904. https://github.com/ericbrasiln/pyHDB
- A ideia de extrair campos dos anúncios é inspirada em https://github.com/luizhenriquesoares/hemeroteca-digital (sem código reaproveitado).
