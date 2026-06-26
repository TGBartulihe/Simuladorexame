"""
investigate_outlier_exams.py — utilitário de diagnóstico (não faz
parte do pipeline). Para cada exame sinalizado como outlier de
contagem, mostra quantos GRUPOS ele tem e quantas questões por grupo —
para distinguir "perdeu questões de verdade" de "esse exame
genuinamente tem menos grupos/itens" (ex: exames de equivalência,
exames antigos com estrutura diferente).

Uso:
    python scripts/investigate_outlier_exams.py --db database/simuladorexame.db --exam-key 2025-639-F1
"""
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--exam-key", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, exam_document_id, criteria_document_id FROM exams WHERE exam_key = ?", (args.exam_key,))
row = cur.fetchone()
if not row:
    print("Exame não encontrado.")
    exit(1)

exam_id = row["id"]
cur.execute(
    "SELECT filename, LENGTH(extracted_text) as len FROM documents WHERE id IN (?, ?)",
    (row["exam_document_id"], row["criteria_document_id"]),
)
print("Documentos associados:")
for r in cur.fetchall():
    print(f"  {r['filename']}: {r['len']} chars extraídos")

print()
cur.execute(
    """
    SELECT g.group_name, COUNT(q.id) as total
    FROM groups_table g
    LEFT JOIN questions q ON q.group_id = g.id
    WHERE g.exam_id = ?
    GROUP BY g.id
    ORDER BY g.display_order
    """,
    (exam_id,),
)
print("Questões por grupo:")
for r in cur.fetchall():
    print(f"  {r['group_name']}: {r['total']} questões")

print()
cur.execute("SELECT question_number, question_type, LENGTH(statement) as len FROM questions WHERE exam_id = ? ORDER BY id", (exam_id,))
print("Todas as questões:")
for r in cur.fetchall():
    print(f"  numero={r['question_number']:>6} tipo={r['question_type']:<15} len={r['len']}")
