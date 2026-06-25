"""
summarize_answers_cache.py — utilitário de diagnóstico (não faz parte
do pipeline). Reconstrói o resumo de uma rodada de extração de gabarito
que já rodou, lendo diretamente o que está em llm_extraction_cache —
útil quando a saída do terminal já rolou para fora da tela / foi
fechada antes de copiar.
"""
import argparse
import json
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
cur = conn.cursor()

cur.execute(
    "SELECT response_json FROM llm_extraction_cache WHERE prompt_version = 'extract-v1'"
)
rows = cur.fetchall()

resolved = 0
descartadas = 0
for (response_json,) in rows:
    parsed = json.loads(response_json)
    letras = parsed.get("letras_corretas") or []
    confianca = parsed.get("confianca", "baixa")
    if letras and confianca != "baixa":
        resolved += 1
    else:
        descartadas += 1

print(f"Total no cache (prompt_version=extract-v1): {len(rows)}")
print(f"Resolvidas (confiança alta/média, gravadas como gabarito): {resolved}")
print(f"Descartadas (sem resposta ou confiança baixa): {descartadas}")

print()
print("=== Estado real das choices no banco (is_correct) ===")
cur.execute(
    """
    SELECT COUNT(DISTINCT q.id) FROM questions q
    JOIN choices c ON c.question_id = q.id
    WHERE q.question_type = 'multiple_choice' AND c.is_correct = 1
    """
)
print(f"Questões multiple_choice com gabarito marcado: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM questions WHERE question_type = 'multiple_choice'")
print(f"Total de questões multiple_choice: {cur.fetchone()[0]}")
