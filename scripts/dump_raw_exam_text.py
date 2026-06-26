"""
dump_raw_exam_text.py — utilitário de diagnóstico (não faz parte do
pipeline). Salva o texto bruto (documents.extracted_text, ANTES de
clean_text) de um exame num arquivo, para inspeção direta — sem
nenhum processamento, para isolar se o problema está na extração do
PDF ou em alguma etapa de limpeza/parsing posterior.

Uso:
    python scripts/dump_raw_exam_text.py --db database/simuladorexame.db --exam-key 2025-639-F1
"""
import argparse
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--exam-key", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute(
    """
    SELECT ex.extracted_text AS exam_text, ex.filename AS exam_filename
    FROM exams e
    JOIN documents ex ON ex.id = e.exam_document_id
    WHERE e.exam_key = ?
    """,
    (args.exam_key,),
)
row = cur.fetchone()
if not row:
    print("Exame não encontrado.")
    exit(1)

out_dir = Path("debug_pilot_output")
out_dir.mkdir(exist_ok=True)
out_path = out_dir / f"raw_{args.exam_key}.txt"
out_path.write_text(row["exam_text"] or "", encoding="utf-8")

print(f"Texto bruto de {row['exam_filename']} salvo em {out_path}")
print(f"Tamanho: {len(row['exam_text'] or '')} chars")
print()
print("=== Primeiros 1000 caracteres ===")
print((row["exam_text"] or "")[:1000])
