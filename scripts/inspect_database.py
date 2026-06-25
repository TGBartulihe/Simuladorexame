import sqlite3
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")

with sqlite3.connect(DB_PATH) as conn:
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    by_type = conn.execute("""
        SELECT document_type, COUNT(*)
        FROM documents
        GROUP BY document_type
    """).fetchall()

    samples = conn.execute("""
        SELECT filename, document_type, LENGTH(extracted_text)
        FROM documents
        ORDER BY filename
        LIMIT 20
    """).fetchall()

print(f"Total de documentos: {total}")
print("\nPor tipo:")
for row in by_type:
    print(row)

print("\nAmostras:")
for filename, doc_type, length in samples:
    print(f"{filename} | {doc_type} | {length} caracteres")
