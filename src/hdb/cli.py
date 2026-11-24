"""Linha de comando: `python -m hdb <etapa> ...`

As etapas gravam no banco (Supabase), então podem ser rodadas separadamente e por várias pessoas.
"""
import argparse
import getpass
from pathlib import Path

from hdb import config
from hdb.banco import BancoSupabase
from hdb.busca import coletar_ocorrencias, nova_sessao


def _banco():
    try:
        return BancoSupabase()
    except RuntimeError as e:
        raise SystemExit(f"erro: {e}")


def cmd_buscar(args):
    salvas, total = coletar_ocorrencias(nova_sessao(), args.bib, args.termo, _banco(), limite=args.limite)
    if total == 0:
        print(f"Nenhuma ocorrência de {args.termo!r} no acervo {args.bib}.")
        return
    print(f"{salvas} de {total} ocorrências de {args.termo!r} no banco.")


def cmd_capturar(args):
    from hdb.captura import capturar

    capturar(_banco(), args.quem, bib=args.bib, termo=args.termo, max_paginas=args.max_paginas,
             aleatorio=args.aleatorio, modo=args.modo, tamanho=args.tamanho, workers=args.workers,
             guardar=args.guardar_imagens)


def cmd_importar(args):
    from hdb.captura import importar_existentes

    importar_existentes(_banco(), args.quem, workers=args.workers)


def cmd_reprocessar(args):
    from hdb.captura import reprocessar

    reprocessar(_banco(), args.quem, args.pasta, workers=args.workers, limite=args.limite)


def cmd_anuncios(args):
    from hdb.captura import anuncios_das_paginas, anuncios_do_arquivo

    if args.palavras:
        anuncios_do_arquivo(args.palavras, args.imagem, args.depurar)
        return
    banco = None if args.sem_banco else _banco()
    anuncios_das_paginas(banco, args.pasta, versao=args.versao, limite=args.limite, depurar=args.depurar,
                         refazer=args.refazer)


def cmd_campos(args):
    from hdb.campos import formatar_resumo, processar

    print(formatar_resumo(processar(_banco(), args.versao_anuncios, args.versao, args.limite)))


def cmd_corpus(args):
    from hdb.corpus import formatar_resumo, processar

    print(formatar_resumo(processar(_banco(), args.versao_campos, args.versao)))


def cmd_topicos(args):
    from hdb.topicos import formatar_resumo, processar

    print(formatar_resumo(processar(_banco(), args.versao_corpus, args.topicos, args.semente, args.versao)))


def cmd_acervos(args):
    from hdb.acervos import descobrir_acervos

    descobrir_acervos(_banco(), args.local, args.periodo, sondas=tuple(args.sonda or config.PANORAMA_SONDAS),
                      limite=args.limite, visivel=(args.modo == "janela"))


def cmd_panorama(args):
    from hdb.acervos import contar_panorama, formatar_ranking, ranking

    banco = _banco()
    contar_panorama(banco, args.local, args.periodo, args.termo, recontar=args.recontar,
                    com_total=not args.sem_total)
    for termo in args.termo:
        print(f"\n{termo} em {args.local}, {args.periodo} (ordem: {args.ordenar})")
        print(formatar_ranking(ranking(banco, args.local, args.periodo, termo, args.ordenar)))


def cmd_relatorio(args):
    from datetime import date

    from hdb.relatorio import montar

    saida = args.saida or config.RAIZ / "relatorios" / f"relatorio_{date.today().isoformat()}.md"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(montar(_banco().relatorio()), encoding="utf-8")
    print(saida)


def cmd_status(args):
    s = _banco().status()
    print("Páginas por status:", _contagens(s["por_status"]) or "nenhuma")
    for titulo, chave in (("Por acervo", "por_acervo"), ("Por termo", "por_termo")):
        print(f"\n{titulo}:")
        for nome, contagens in s[chave].items():
            print(f"  {nome}: {_contagens(contagens)}")
    print("\nÚltimos erros:")
    for e in s["ultimos_erros"] or []:
        print(f"  {e['quando'][:19]} {e['bib']} p.{e['pagina_fisica']} [{e['etapa']}] {e['erro']}")
    por_captcha = s["paginas_por_captcha"]
    print(f"\nPáginas por CAPTCHA: {por_captcha if por_captcha is not None else 'sem CAPTCHA registrado'}")


def _contagens(contagens):
    return ", ".join(f"{n} {status}" for status, n in sorted(contagens.items()))


def criar_parser():
    parser = argparse.ArgumentParser(prog="hdb", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("buscar", help="registra no banco as páginas com ocorrência de um termo num acervo")
    p.add_argument("--bib", required=True, help="código do acervo, ex.: 364568_04")
    p.add_argument("--termo", required=True, help='termo sem acento; expressões exatas entre aspas duplas')
    p.add_argument("--limite", type=int, help="máximo de ocorrências (padrão: todas)")
    p.set_defaults(func=cmd_buscar)

    p = sub.add_parser("capturar", help="captura as páginas pendentes e grava o texto do OCR no banco "
                                        "(uma pessoa resolve o CAPTCHA)")
    p.add_argument("--quem", default=getpass.getuser(), help="quem captura, para a reserva (padrão: usuário do sistema)")
    p.add_argument("--bib", help="só as páginas deste acervo")
    p.add_argument("--termo", help="só as páginas com ocorrência deste termo")
    p.add_argument("--max-paginas", type=int, default=config.MAX_PAGINAS,
                   help=f"máximo de páginas por execução (padrão: {config.MAX_PAGINAS})")
    p.add_argument("--aleatorio", action="store_true", help="sorteia as páginas em vez de seguir a ordem do acervo")
    p.add_argument("--modo", choices=("terminal", "janela"), default="terminal",
                   help="onde a pessoa resolve o CAPTCHA (padrão: terminal)")
    p.add_argument("--workers", type=int, default=config.OCR_WORKERS,
                   help=f"processos de OCR em paralelo (padrão: {config.OCR_WORKERS})")
    p.add_argument("--guardar-imagens", metavar="DIR", help="mantém uma cópia de cada imagem em DIR/<bib>/")
    p.add_argument("--tamanho", default=config.TAMANHO_HIRES, help="resolução pedida à HDB")
    p.set_defaults(func=cmd_capturar)

    p = sub.add_parser("importar", help="carrega no banco os CSVs de data/ocorrencias/, as contagens "
                                        "e páginas por acervo de data/ e o OCR das imagens de data/imagens/")
    p.add_argument("--quem", default=getpass.getuser(), help="nome registrado nas tentativas")
    p.add_argument("--workers", type=int, default=config.OCR_WORKERS, help="processos de OCR em paralelo")
    p.set_defaults(func=cmd_importar)

    p = sub.add_parser("reprocessar", help="refaz o OCR de imagens que já estão no disco e grava a nova leitura, "
                                           "comparando com a anterior")
    p.add_argument("--pasta", nargs="+", type=Path, default=list(config.PASTAS_REPROCESSAR),
                   help="pastas com <bib>/<bib>_<página>.jpg (padrão: data/amostra, data/falhas_ocr e data/imagens)")
    p.add_argument("--quem", default=getpass.getuser(), help="nome registrado nas tentativas")
    p.add_argument("--workers", type=int, default=config.OCR_WORKERS,
                   help=f"processos de OCR em paralelo (padrão: {config.OCR_WORKERS})")
    p.add_argument("--limite", type=int, help="máximo de imagens (padrão: todas)")
    p.set_defaults(func=cmd_reprocessar)

    p = sub.add_parser("anuncios", help="separa as páginas já lidas em colunas e anúncios (heurístico) e grava no banco")
    p.add_argument("--pasta", nargs="+", type=Path, default=list(config.PASTAS_REPROCESSAR),
                   help="pastas com <bib>/<bib>_<página>.jpg (padrão: as mesmas de `reprocessar`)")
    p.add_argument("--versao", default=config.VERSAO_ANUNCIOS,
                   help=f"versão da segmentação; regravar a mesma substitui (padrão: {config.VERSAO_ANUNCIOS})")
    p.add_argument("--limite", type=int, help="máximo de imagens (padrão: todas)")
    p.add_argument("--refazer", action="store_true",
                   help="reprocessa também as páginas que já têm anúncios nessa versão (padrão: pula)")
    p.add_argument("--depurar", metavar="DIR", type=Path,
                   help="grava em DIR um PNG por página com as colunas e os anúncios, para revisão visual")
    p.add_argument("--sem-banco", action="store_true", help="não grava no banco (nem precisa de acesso a ele)")
    p.add_argument("--quem", default=getpass.getuser(), help="quem roda (por ora só informativo)")
    p.add_argument("--palavras", type=Path, help="JSON de palavras já pronto: segmenta só ele, sem OCR nem banco")
    p.add_argument("--imagem", type=Path, help="com --palavras: a imagem, para a depuração")
    p.set_defaults(func=cmd_anuncios)

    p = sub.add_parser("campos", help="classifica os anúncios (fuga, venda, aluguel...) e extrai sexo, idade, nação, "
                                      "nome etc. (heurístico) e grava no banco")
    p.add_argument("--versao-anuncios", default=config.VERSAO_ANUNCIOS,
                   help=f"versão da segmentação a processar (padrão: {config.VERSAO_ANUNCIOS})")
    p.add_argument("--versao", default=config.VERSAO_CAMPOS,
                   help=f"versão da extração; regravar a mesma substitui (padrão: {config.VERSAO_CAMPOS})")
    p.add_argument("--limite", type=int, help="máximo de anúncios (padrão: todos)")
    p.set_defaults(func=cmd_campos)

    p = sub.add_parser("corpus", help="seleciona os anúncios de pessoas escravizadas e grava o texto padronizado "
                                      "(para a modelagem de tópicos) ao lado do original")
    p.add_argument("--versao-campos", default=config.VERSAO_CAMPOS,
                   help=f"versão dos campos (tipo) a usar na seleção (padrão: {config.VERSAO_CAMPOS})")
    p.add_argument("--versao", default=config.VERSAO_CORPUS,
                   help=f"versão do corpus; regravar a mesma substitui (padrão: {config.VERSAO_CORPUS})")
    p.set_defaults(func=cmd_corpus)

    p = sub.add_parser("topicos", help="modelagem de tópicos (LDA) sobre o corpus padronizado; grava palavras e "
                                       "misturas por anúncio")
    p.add_argument("--versao-corpus", default=config.VERSAO_CORPUS,
                   help=f"versão do corpus a modelar (padrão: {config.VERSAO_CORPUS})")
    p.add_argument("--topicos", type=int, default=config.N_TOPICOS,
                   help=f"número de tópicos (padrão: {config.N_TOPICOS})")
    p.add_argument("--semente", type=int, default=config.SEMENTE_TOPICOS,
                   help=f"semente do LDA (padrão: {config.SEMENTE_TOPICOS})")
    p.add_argument("--versao", default=config.VERSAO_TOPICOS,
                   help=f"versão do modelo; regravar a mesma substitui (padrão: {config.VERSAO_TOPICOS})")
    p.set_defaults(func=cmd_topicos)

    p = sub.add_parser("acervos", help="descobre os periódicos de um estado e década na HDB e grava o código (bib) "
                                       "de cada um")
    p.add_argument("--local", required=True, help="estado, como na tela da HDB, ex.: RJ")
    p.add_argument("--periodo", required=True, help='década, ex.: "1850 - 1859"')
    p.add_argument("--sonda", action="append",
                   help="palavra usada para abrir o leitor de cada periódico; repita para dar reservas "
                        f"(padrão: {', '.join(config.PANORAMA_SONDAS)})")
    p.add_argument("--limite", type=int, help="máximo de periódicos consultados nesta execução (padrão: todos)")
    p.add_argument("--modo", choices=("terminal", "janela"), default="terminal",
                   help="terminal: navegador oculto; janela: navegador visível (padrão: terminal)")
    p.set_defaults(func=cmd_acervos)

    p = sub.add_parser("panorama", help="conta em quantas páginas de cada periódico de um estado e década "
                                        "aparece um termo e mostra o ranking")
    p.add_argument("--local", required=True, help="estado, ex.: RJ")
    p.add_argument("--periodo", required=True, help='década, ex.: "1850 - 1859"')
    p.add_argument("--termo", action="append", required=True, help="termo da busca; repita para vários")
    p.add_argument("--recontar", action="store_true", help="refaz as contagens que já estão no banco")
    p.add_argument("--sem-total", action="store_true",
                   help="não calcula o total de páginas dos acervos (sem ele não há percentual)")
    p.add_argument("--ordenar", choices=("paginas", "percentual"), default="paginas",
                   help="critério do ranking (padrão: paginas)")
    p.set_defaults(func=cmd_panorama)

    p = sub.add_parser("relatorio", help="gera o relatório metodológico (Markdown) a partir do banco")
    p.add_argument("--saida", type=Path,
                   help="arquivo de saída (padrão: relatorios/relatorio_<AAAA-MM-DD>.md na raiz do projeto)")
    p.set_defaults(func=cmd_relatorio)

    p = sub.add_parser("status", help="mostra o andamento: páginas por status, acervo e termo, e erros")
    p.set_defaults(func=cmd_status)
    return parser


def main(argv=None):
    args = criar_parser().parse_args(argv)
    args.func(args)
