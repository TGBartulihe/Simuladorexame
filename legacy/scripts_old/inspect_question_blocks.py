import sqlite3
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")

with sqlite3.connect(DB_PATH) as conn:
    total = conn.execute("SELECT COUNT(*) FROM question_blocks").fetchone()[0]

    by_subject = conn.execute("""
        SELECT e.subject, COUNT(*)
        FROM question_blocks qb
        JOIN exams e ON e.id = qb.exam_id
        GROUP BY e.subject
        ORDER BY e.subject
    """).fetchall()

    samples = conn.execute("""
        SELECT
            e.exam_key,
            e.subject,
            qb.group_name,
            qb.question_number,
            LENGTH(qb.raw_statement),
            LENGTH(qb.raw_criteria),
            substr(qb.raw_statement, 1, 300)
        FROM question_blocks qb
        JOIN exams e ON e.id = qb.exam_id
        ORDER BY e.year DESC, e.subject, e.phase, qb.id
        LIMIT 20
    """).fetchall()

print(f"Total de blocos: {total}")

print("\nPor disciplina:")
for row in by_subject:
    print(row)

print("\nAmostras:")
for row in samples:
    print("=" * 80)
    print(row[0], "|", row[1], "|", row[2], "| Q", row[3])
    print("statement chars:", row[4], "| criteria chars:", row[5])
    print(row[6])