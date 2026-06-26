"""
inspect_documents_table.py — utilitário de diagnóstico (não faz parte
do pipeline). Verifica se documents.extracted_text já tem clean_text()
aplicado (texto "limpo") ou é o texto bruto direto do PDFExtractor
(com marcadores "--- PAGE N ---" ainda presentes).

Isso é decisivo para entender por que o reprocessamento via
process_parser_v2 deu um resultado diferente do teste piloto
(que chama PDFExtractor + clean_text diretamente nos PDFs).

Uso:
    python scripts/inspect_documents_table.py --db database/simuladorexame.db
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
    "SELECT id, filename, document_type, extracted_text FROM documents WHERE filename LIKE '%BG702-F1-2025%'"
)
rows = cur.fetchall()
print(f"{len(rows)} documentos encontrados para BG702-F1-2025\n")

for r in rows:
    text = r["extracted_text"] or ""
    has_page_marker = "--- PAGE" in text
    has_iave_header = "INSTITUTO DE AVALIA" in text.upper() or text.upper().count("IAVE") > 0
    print(f"id={r['id']} filename={r['filename']} type={r['document_type']}")
    print(f"  tamanho do texto: {len(text)} chars")
    print(f"  contém marcador '--- PAGE N ---'? {has_page_marker}")
    print(f"  contém referência a IAVE/INSTITUTO (timbre ainda presente)? {has_iave_header}")
    print(f"  contém a frase da questão 4 do GRUPO III (Instituto Português do Mar)? {'Instituto Português do Mar' in text}")
    print(f"  primeiros 200 chars: {text[:200]!r}")
    print()
