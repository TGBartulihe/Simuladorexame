"""
inspect_cache.py — utilitário de diagnóstico (não faz parte do pipeline).

Mostra o conteúdo já cacheado em llm_extraction_cache, para entender o que
o LLM respondeu sem precisar chamar o Ollama de novo. Útil depois de uma
rodada com --limit pequeno, antes de decidir escalar.
"""
import argparse
import json
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--prompt-version", default="extract-v1")
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute(
    """
    SELECT c.question_id, q.statement, c.response_json
    FROM llm_extraction_cache c
    JOIN questions q ON q.id = c.question_id
    WHERE c.prompt_version = ?
    ORDER BY c.question_id
    """,
    (args.prompt_version,),
)
rows = cur.fetchall()
print(f"{len(rows)} itens cacheados para prompt_version={args.prompt_version}\n")

for r in rows:
    parsed = json.loads(r["response_json"])
    statement_preview = (r["statement"] or "").strip().replace("\n", " ")[:90]
    print(f"qid={r['question_id']} | {statement_preview}...")
    print(f"  -> {parsed}")
    print()
