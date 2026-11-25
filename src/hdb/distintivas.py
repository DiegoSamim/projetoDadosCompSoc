"""Palavras que distinguem um grupo dos demais (log-odds ponderado com prior informativo).

Função pura: recebe contagens de palavras por grupo e devolve, por grupo, as palavras mais "dele".
"""
import math
from collections import Counter

A0_PADRAO = 500  # força do prior (soma dos pseudo-contadores), como em Monroe, Colaresi e Quinn (2008)


def palavras_distintivas(contagens, n=10, z_min=1.96, prior=None):
    """{grupo: [(palavra, z, n_no_grupo)]}: as até `n` palavras com z >= `z_min`, da maior para a menor.

    `contagens = {grupo: Counter de palavras}`. Cada grupo é comparado com TODOS os outros juntos.

    Fórmula (Monroe, Colaresi e Quinn 2008, "Fightin' Words", eq. 16 e 22), para a palavra w, o grupo i e o resto j:
        a_w   = a0 * freq_global(w)        (prior informativo: proporcional à frequência da palavra em todo o corpus;
                                            a0 = soma do prior)
        delta = log((y_iw + a_w) / (n_i + a0 - y_iw - a_w)) - log((y_jw + a_w) / (n_j + a0 - y_jw - a_w))
        var   ~ 1 / (y_iw + a_w) + 1 / (y_jw + a_w)
        z     = delta / sqrt(var)
    onde y_iw é a contagem de w no grupo i, n_i o total de palavras do grupo i (y_jw, n_j: o resto).
    z >= 1,96 corresponde a ~95% de confiança (unilateral 97,5%) de que a palavra é mais frequente no grupo.

    `prior`: None (a0 = min(500, 0,1 x total de palavras), repartido pela frequência global) ou um Counter/dict
    palavra -> pseudo-contador já pronto (a0 = sua soma).
    """
    total = Counter()
    for c in contagens.values():
        total.update(c)
    soma_total = sum(total.values())
    if soma_total == 0:
        return {g: [] for g in contagens}
    if prior is None:
        a0 = min(A0_PADRAO, 0.1 * soma_total)
        alfa = {w: a0 * v / soma_total for w, v in total.items()}
    else:
        alfa = {w: float(prior.get(w, 0)) for w in total}
        a0 = sum(alfa.values())
    saida = {}
    for grupo, c in contagens.items():
        n_i = sum(c.values())
        n_j = soma_total - n_i
        lista = []
        for w, y_i in c.items():
            a = alfa.get(w, 0.0)
            y_j = total[w] - y_i
            if y_i <= 0 or a <= 0:
                continue
            den_i, den_j = n_i + a0 - y_i - a, n_j + a0 - y_j - a
            if den_i <= 0 or den_j <= 0:
                continue
            delta = math.log((y_i + a) / den_i) - math.log((y_j + a) / den_j)
            z = delta / math.sqrt(1 / (y_i + a) + 1 / (y_j + a))
            if z >= z_min:
                lista.append((w, float(z), int(y_i)))
        lista.sort(key=lambda x: (-x[1], x[0]))
        saida[grupo] = lista[:n]
    return saida
