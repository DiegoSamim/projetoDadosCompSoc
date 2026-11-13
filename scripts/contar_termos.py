"""Conta, em cada acervo da HDB, em quantas páginas aparece cada palavra ou frase (só leitura).

Não precisa de CAPTCHA nem de banco: é uma requisição por par (termo, acervo), com a pausa de
sempre. O resultado vai para data/contagens_termos.csv e é retomável: rodar de novo pula o que já
foi contado. Para acrescentar termos, edite TERMOS e rode outra vez.

    PYTHONPATH=src python scripts/contar_termos.py            # conta tudo o que falta
    PYTHONPATH=src python scripts/contar_termos.py --categoria fuga
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hdb import config  # noqa: E402
from hdb.busca import nova_sessao, total_ocorrencias  # noqa: E402

SAIDA = config.DATA_DIR / "contagens_termos.csv"

# (código do acervo, rótulo curto). "JC" = Jornal do Commercio (RJ); "DRJ" = Diário do Rio de Janeiro.
ACERVOS = [
    ("364568_01", "JC 1827–29"),
    ("364568_02", "JC 1830s"),
    ("364568_03", "JC 1840s"),
    ("364568_04", "JC 1850s"),
    ("364568_05", "JC 1860s"),
    ("364568_06", "JC 1870s"),
    ("364568_07", "JC 1880s"),
    ("094170_01", "DRJ 1821–58"),
    ("094170_02", "DRJ 1860–78"),
]

# Como a busca da HDB se comporta (verificado em nov/2026):
#   - ignora maiúsculas e acentos ("nação" = "nacao") e normaliza parte da grafia antiga
#     ("apprehender" ≈ "apreender");
#   - aspas duplas = frase exata (palavras coladas); sem aspas, várias palavras = todas na mesma página;
#   - "*" no fim da palavra funciona ("escrav*" pega escravo, escrava, escravos...);
#   - palavras muito comuns ("de") são ignoradas e devolvem 0;
#   - "fugio" e "fugiu" são palavras diferentes: as duas grafias existem e são contadas.
TERMOS = {
    "curinga": [  # "*" junta as variações de gênero e número numa busca só
        "escrav*", "fugid*", "gratific*", "negr*", "crioul*",
        '"escrav* fugid*"', '"fugi* o escrav*"',
    ],
    "fuga": [  # frases de anúncio de fuga: as mais específicas
        '"escravo fugido"', '"escrava fugida"', '"escravos fugidos"',
        '"fugio o escravo"', '"fugio a escrava"', '"fugio um escravo"', '"fugio uma escrava"',
        '"fugiu o escravo"', '"fugiu a escrava"', '"fugiu um escravo"', '"fugiu uma escrava"',
        '"escravo fugio"', '"escrava fugio"', '"escravo fugiu"', '"escrava fugiu"',
        '"preto fugido"', '"preta fugida"', '"crioulo fugido"', '"crioula fugida"',
        '"negro fugido"', '"negra fugida"', '"pardo fugido"',
        '"fugio o preto"', '"fugio a preta"', '"fugio o crioulo"', '"fugio o negro"', '"fugio o pardo"',
        "fugio", "fugiu", "fugido", "fugida", "fugidos",
    ],
    "recompensa": [  # o anúncio de fuga quase sempre oferece recompensa
        "gratifica", "gratificação", "apprehender", "apprehendido", "calabouço",
        '"quem o apprehender"', '"quem o pegar"', '"quem o levar"', '"recolher a cadeia"',
    ],
    "descricao": [  # origem e sinais que descrevem a pessoa anunciada
        "boçal", "ladino", "benguela", "cabinda", "congo", "monjolo", "rebolo", "nagô", "fula",
        '"de nação"', "signaes", "cicatrizes",
    ],
    "comercio": [  # compra, venda e aluguel
        '"vende-se um escravo"', '"vende-se uma escrava"', '"vendem-se escravos"',
        '"vende-se uma preta"', '"vende-se um crioulo"',
        '"compra-se escravos"', '"compram-se escravos"', '"compra-se um escravo"',
        '"aluga-se um escravo"', '"aluga-se uma escrava"', '"alugam-se escravos"',
        '"escravo de ganho"', '"preta de ganho"',
        '"ama de leite"', '"amas de leite"', '"ama secca"',
        # outras palavras de época para a pessoa anunciada
        '"vende-se um preto"', '"vende-se uma crioula"', '"vende-se um moleque"', '"vende-se uma parda"',
        '"vende-se um pardo"', '"vende-se uma negra"', '"vende-se um negro"', '"vendem-se pretos"',
        '"compra-se uma escrava"', '"compra-se um preto"', '"compra-se uma preta"', '"compra-se um moleque"',
        '"compra-se uma crioula"',
        '"aluga-se uma preta"', '"aluga-se um preto"', '"aluga-se uma crioula"', '"aluga-se uma parda"',
        '"aluga-se um moleque"', '"alugam-se pretas"',
        # ama de leite: "ama de leite" sozinho serve a livres e a escravizadas
        '"preta com leite"', '"escrava com leite"', '"crioula com leite"',
        '"ama de leite" preta', '"ama de leite" escrava', '"ama de leite" crioula',
    ],
    "pessoas": [  # palavras soltas: muito frequentes, pouca precisão sozinhas
        "escravos", "escravas", "preto", "preta", "pretos", "pretas",
        "negro", "negra", "negros", "negras", "crioulo", "crioula", "crioulos",
        "pardo", "parda", "mulato", "mulata", "moleque", "molecote",
        "africano", "africana", "cativo", "captivo",
    ],
    "liberdade_e_lei": [  # contexto histórico e legal (não são anúncios de pessoas)
        "alforria", '"carta de liberdade"', "forro", "liberto", "ingenuo", '"ventre livre"',
        "sexagenario", '"fundo de emancipação"', "tráfico", "contrabando",
    ],
}

CAMPOS = ["categoria", "termo", "bib", "acervo", "paginas", "coletado_em"]


def ja_contados():
    if not SAIDA.exists():
        return set()
    with open(SAIDA, newline="", encoding="utf-8") as f:
        return {(l["termo"], l["bib"]) for l in csv.DictReader(f)}


def gravar(linha):
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    novo = not SAIDA.exists()
    with open(SAIDA, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        w.writerow(linha)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--categoria", choices=list(TERMOS), help="só esta categoria (padrão: todas)")
    args = parser.parse_args()

    feitos = ja_contados()
    sessao = nova_sessao()
    categorias = [args.categoria] if args.categoria else list(TERMOS)
    pares = [(c, t, bib, nome) for c in categorias for t in TERMOS[c] for bib, nome in ACERVOS
             if (t, bib) not in feitos]
    print(f"{len(pares)} contagens a fazer (cerca de {len(pares) * 3.6 / 60:.0f} min).", flush=True)
    for i, (categoria, termo, bib, nome) in enumerate(pares, 1):
        try:
            n = total_ocorrencias(sessao, bib, termo)
        except Exception as e:  # fica sem registro: uma nova execução tenta de novo
            print(f"[{i}/{len(pares)}] {termo} / {bib}: erro ({type(e).__name__})", flush=True)
            continue
        gravar({"categoria": categoria, "termo": termo, "bib": bib, "acervo": nome, "paginas": n,
                "coletado_em": datetime.now().isoformat(timespec="seconds")})
        print(f"[{i}/{len(pares)}] {termo:28} {nome:12} {n}", flush=True)


if __name__ == "__main__":
    main()
