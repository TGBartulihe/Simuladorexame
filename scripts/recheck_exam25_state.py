"""
recheck_exam25_state.py — utilitário de diagnóstico (não faz parte do
pipeline). Olha o estado REAL e ATUAL da tabela `questions` para
exam_id=25, sem reprocessar nada — só lendo o que está gravado agora,
depois do `process_parser_v2` que você já rodou.

Uso:
    python scripts/recheck_exam25_state.py --db database/simuladorexame.db
"""
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, exam_key, exam_document_id, criteria_document_id FROM exams WHERE exam_key = '2025-702-F1'")
exam_row = cur.fetchone()
print(f"exam_id={exam_row['id']}, exam_document_id={exam_row['exam_document_id']}, criteria_document_id={exam_row['criteria_document_id']}")
print()

cur.execute(
    "SELECT id, question_number, question_type, LENGTH(statement) as len FROM questions WHERE exam_id = ? ORDER BY id",
    (exam_row["id"],),
)
rows = cur.fetchall()
print(f"Questões REAIS no banco agora para exam_id={exam_row['id']}: {len(rows)}")
for r in rows:
    print(f"  id={r['id']} numero={r['question_number']:>6} tipo={r['question_type']:<15} len={r['len']}")

print()
print("=== Há mais de um exam_id com exam_key parecido? (ex: duplicata de exame) ===")
cur.execute("SELECT id, exam_key FROM exams WHERE exam_key LIKE '%702-F1%' AND year=2025")
for r in cur.fetchall():
    print(f"  exam_id={r['id']} exam_key={r['exam_key']}")
