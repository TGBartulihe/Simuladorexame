"""
inspect_question_counts.py — utilitário de diagnóstico (não faz parte
do pipeline). Investiga se o aumento no número de questões depois do
reprocessamento é legítimo (questões reais que antes eram perdidas) ou
um efeito colateral indesejado (duplicatas, fragmentos espúrios).

Uso:
    python scripts/inspect_question_counts.py --db database/simuladorexame.db
"""
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== Distribuição de questões por exame (estatísticas) ===")
cur.execute(
    """
    SELECT e.exam_key, e.subject, COUNT(q.id) as total
    FROM exams e
    JOIN questions q ON q.exam_id = e.id
    GROUP BY e.id
    ORDER BY total DESC
    LIMIT 10
    """
)
print("Top 10 exames com MAIS questões (suspeitos de duplicação):")
for r in cur.fetchall():
    print(f"  {r['exam_key']} ({r['subject']}): {r['total']} questões")

print()
cur.execute(
    """
    SELECT e.exam_key, e.subject, COUNT(q.id) as total
    FROM exams e
    JOIN questions q ON q.exam_id = e.id
    GROUP BY e.id
    ORDER BY total ASC
    LIMIT 10
    """
)
print("Top 10 exames com MENOS questões:")
for r in cur.fetchall():
    print(f"  {r['exam_key']} ({r['subject']}): {r['total']} questões")

print()
print("=== Checando duplicatas de question_number dentro do mesmo exame ===")
cur.execute(
    """
    SELECT exam_id, question_number, COUNT(*) as n
    FROM questions
    GROUP BY exam_id, question_number
    HAVING COUNT(*) > 1
    """
)
dupes = cur.fetchall()
print(f"Pares (exam_id, question_number) duplicados: {len(dupes)}")
for r in dupes[:15]:
    print(f"  exam_id={r['exam_id']} numero={r['question_number']!r} ocorrencias={r['n']}")

print()
print("=== Amostra de statements muito curtos (possíveis fragmentos espúrios) ===")
cur.execute(
    """
    SELECT id, exam_id, question_number, question_type, LENGTH(statement) as len, statement
    FROM questions
    WHERE LENGTH(statement) < 150
    ORDER BY len ASC
    LIMIT 15
    """
)
for r in cur.fetchall():
    preview = (r["statement"] or "")[:80].replace("\n", " ")
    print(f"  id={r['id']} exam={r['exam_id']} num={r['question_number']} len={r['len']} tipo={r['question_type']}: {preview!r}")

print()
print(f"Total de questões com statement < 150 chars: ", end="")
cur.execute("SELECT COUNT(*) FROM questions WHERE LENGTH(statement) < 150")
print(cur.fetchone()[0])

print()
print("=== Comparação direta: exam_id do exame piloto (Biologia 2025 F1) ===")
cur.execute("SELECT id FROM exams WHERE exam_key = '2025-702-F1'")
row = cur.fetchone()
if row:
    exam_id = row["id"]
    cur.execute("SELECT COUNT(*) FROM questions WHERE exam_id = ?", (exam_id,))
    print(f"Questões no exame piloto agora: {cur.fetchone()[0]} (esperado: 34, confirmado no teste piloto)")
