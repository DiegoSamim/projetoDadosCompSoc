"""Leitura dos CSVs da primeira versão da coleta, usados por `hdb importar`."""
import csv
from pathlib import Path


def ler_csv_parcial(caminho):
    """Linhas já salvas (lista de dicts). Lista vazia se o arquivo não existe."""
    caminho = Path(caminho)
    if not caminho.exists():
        return []
    with open(caminho, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:  # o CSV devolve tudo como texto; os contadores voltam a ser números
        for campo in ("ocorrencia", "total_ocorrencias"):
            if linha.get(campo):
                linha[campo] = int(linha[campo])
    return linhas
