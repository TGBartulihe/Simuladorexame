"""
inspect_truncated_statement_v2.py — utilitário de diagnóstico (não faz
parte do pipeline). Versão corrigida: usa question_id direto do banco
(não um grep textual ambíguo) para achar exatamente a questão truncada
e mostrar o que vem depois dela no texto bruto do grupo certo.

Uso:
    python scripts/inspect_truncated_statement_v2.py --db database/simuladorexame.db --question-id 12345
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
parser.add_argument("--question-id", required=True, type=int)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute(
    """
    SELECT q.id, q.exam_id, q.group_id, q.question_number, q.statement,
           e.exam_key, g.group_name
    FROM questions q
    JOIN exams e ON e.id = q.exam_id
    LEFT JOIN groups_table g ON g.id = q.group_id
    WHERE q.id = ?
    """,
    (args.question_id,),
)
row = cur.fetchone()
if not row:
    print(f"question_id {args.question_id} não encontrado.")
    sys.exit(1)

print(f"exam_key={row['exam_key']} group={row['group_name']} (group_id={row['group_id']}) numero={row['question_number']}")
print(f"statement gravado no banco ({len(row['statement'])} chars): {row['statement']!r}")
print()

# reprocessa o exame do zero para achar o texto bruto correspondente
cur.execute(
    "SELECT ex.extracted_text AS exam_text FROM exams e JOIN documents ex ON ex.id = e.exam_document_id WHERE e.id = ?",
    (row["exam_id"],),
)
exam_text_row = cur.fetchone()
exam_text = clean_text(exam_text_row["exam_text"] or "")
exam_pages = split_pages(exam_text)
groups = parse_groups(exam_id=row["exam_id"], pages=exam_pages)

target_group = next((g for g in groups if g.name == row["group_name"]), None)
if not target_group:
    print(f"Grupo {row['group_name']!r} não encontrado entre os grupos reprocessados.")
    sys.exit(1)

# acha a posição EXATA do statement gravado dentro do texto bruto do grupo,
# usando os primeiros ~40 caracteres do statement como âncora (mais preciso
# que buscar só pelo número, que se repete várias vezes)
anchor = row["statement"][:40]
idx = target_group.text.find(anchor)
if idx == -1:
    print(f"Âncora {anchor!r} não encontrada no texto bruto do grupo — o texto pode ter mudado entre extrações.")
    sys.exit(1)

print(f"Encontrado no texto bruto do grupo, posição {idx}")
print("=== Texto bruto a partir daqui (400 caracteres) ===")
print(repr(target_group.text[idx : idx + 400]))
