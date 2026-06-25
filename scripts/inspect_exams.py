import sqlite3
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")

with sqlite3.connect(DB_PATH) as conn:
    total = conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0]

    by_subject = conn.execute("""
        SELECT subject, COUNT(*)
        FROM exams
        GROUP BY subject
        ORDER BY subject
    """).fetchall()

    missing = conn.execute("""
        SELECT exam_key, subject, year, phase, exam_document_id, criteria_document_id
        FROM exams
        WHERE exam_document_id IS NULL OR criteria_document_id IS NULL
        ORDER BY year DESC, subject, phase
        LIMIT 30
    """).fetchall()

    samples = conn.execute("""
        SELECT exam_key, subject, year, phase, exam_document_id, criteria_document_id
        FROM exams
        ORDER BY year DESC, subject, phase
        LIMIT 40
    """).fetchall()

print(f"Total de exames agrupados: {total}")

print("\nPor disciplina:")
for row in by_subject:
    print(row)

print("\nAmostras:")
for row in samples:
    print(row)

print("\nCom documentos em falta:")
for row in missing:
    print(row)