"""
check_overwritten_content.py — utilitário de diagnóstico (não faz parte
do pipeline). Mostra o STATEMENT completo de cada questão de exam_id=25
para confirmar qual grupo "venceu" o conflito de UNIQUE(exam_id,
question_number) e sobrescreveu as outras.

Uso:
    python scripts/check_overwritten_content.py --db database/simuladorexame.db
"""
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute(
    "SELECT id, group_id, question_number, statement FROM questions WHERE exam_id = 25 ORDER BY id"
)
for r in cur.fetchall():
    print(f"id={r['id']} group_id={r['group_id']} numero={r['question_number']}")
    print(f"  statement: {r['statement']!r}")
    print()
