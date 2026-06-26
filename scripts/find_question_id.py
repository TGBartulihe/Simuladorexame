"""
find_question_id.py — utilitário de diagnóstico (não faz parte do
pipeline). Acha o question_id exato a partir de exam_key +
question_number, para usar com inspect_truncated_statement_v2.py.

Uso:
    python scripts/find_question_id.py --db database/simuladorexame.db --exam-key 2014-702-F1 --question-number 1
"""
import argparse
import sqlite3

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
    SELECT q.id, q.question_number, g.group_name, LENGTH(q.statement) as len, q.statement
    FROM questions q
    JOIN exams e ON e.id = q.exam_id
    LEFT JOIN groups_table g ON g.id = q.group_id
    WHERE e.exam_key = ? AND q.question_number = ?
    """,
    (args.exam_key, args.question_number),
)
rows = cur.fetchall()
print(f"{len(rows)} questão(ões) encontrada(s) com numero={args.question_number!r} em {args.exam_key}:")
for r in rows:
    preview = (r["statement"] or "")[:60].replace("\n", " ")
    print(f"  id={r['id']} grupo={r['group_name']} len={r['len']}: {preview!r}")
