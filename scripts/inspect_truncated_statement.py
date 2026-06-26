"""
inspect_truncated_statement.py — utilitário de diagnóstico (não faz
parte do pipeline). Investiga por que um statement está sendo
truncado no meio da frase, mostrando o texto bruto do grupo ANTES do
parse_questions, para ver o que vem imediatamente depois do trecho
capturado.

Uso:
    python scripts/inspect_truncated_statement.py --db database/simuladorexame.db --exam-key 2014-702-F1 --question-number 1
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser.utils.clean_text import clean_text
from parser.utils.split_pages import split_pages
from parser.parse.parse_groups import parse_groups

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--exam-key", required=True)
parser.add_argument("--question-number", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute(
    """
    SELECT e.id, ex.extracted_text AS exam_text
    FROM exams e
    JOIN documents ex ON ex.id = e.exam_document_id
    WHERE e.exam_key = ?
    """,
    (args.exam_key,),
)
row = cur.fetchone()
if not row:
    print(f"Exame {args.exam_key} não encontrado.")
    sys.exit(1)

exam_text = clean_text(row["exam_text"] or "")
exam_pages = split_pages(exam_text)
groups = parse_groups(exam_id=row["id"], pages=exam_pages)

# acha qual grupo contém a question_number procurada, procurando o texto
# bruto por "N. " seguido do trecho que sabemos estar truncado
target = f"\n{args.question_number}."
for group in groups:
    idx = group.text.find(target)
    if idx == -1:
        # tenta sem a quebra de linha no início (pode ser a 1a linha do grupo)
        if group.text.startswith(f"{args.question_number}."):
            idx = 0
        else:
            continue

    print(f"Encontrado em {group.name}, posição {idx}")
    print("=== Texto bruto a partir da questão (300 caracteres) ===")
    print(repr(group.text[idx : idx + 300]))
    break
else:
    print(f"Questão {args.question_number} não encontrada em nenhum grupo (texto bruto).")
