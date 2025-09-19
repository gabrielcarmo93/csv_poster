# utils/csv_utils.py
import csv

def read_csv_preview(file_path, delimiter=",", num_lines=3):
    """
    Lê as primeiras linhas de um CSV para exibir como preview.
    Retorna uma lista de dicionários (cada linha representada como dict).
    """
    preview = []
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        for i, row in enumerate(reader):
            if i >= num_lines:
                break
            preview.append(row)
    return preview

def read_csv_rows(file_path, delimiter=","):
    """
    Lê todas as linhas de um CSV.
    Retorna uma lista de dicionários.
    """
    rows = []
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        for row in reader:
            rows.append(row)
    return rows
