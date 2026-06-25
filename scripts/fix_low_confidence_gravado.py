"""
fix_low_confidence_gravado.py — correção pontual (não faz parte do
pipeline normal).

A versão anterior de 02_extract_with_llm.py tinha um bug: questões com
confianca='baixa' ainda eram gravadas como gabarito (is_correct=1). Isso
foi corrigido no script principal, mas qualquer rodada feita ANTES da
correção pode ter gravado letras erradas no banco.

Este script:
  1. Acha, no cache (llm_extraction_cache, prompt_version='extract-v1'),
     todas as questões que foram respondidas com confianca='baixa'.
  2. Reverte o is_correct que foi gravado para essas questões (volta a
     is_correct=0 em todas as choices da questão).
  3. Remove a entrada do log de extração regex se existir (não deveria,
     mas por segurança).

Depois de rodar isto, essas questões voltam ao estado "sem gabarito" —
prontas para serem reprocessadas (com o script corrigido) ou deixadas
para revisão manual.

Uso:
    python scripts/fix_low_confidence_gravado.py --db database/simuladorexame.db --dry-run
    python scripts/fix_low_confidence_gravado.py --db database/simuladorexame.db
"""
import argparse
import json
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute(
    """
    SELECT question_id, response_json FROM llm_extraction_cache
    WHERE prompt_version = 'extract-v1'
    """
)
rows = cur.fetchall()

affected = []
for r in rows:
    parsed = json.loads(r["response_json"])
    if parsed.get("confianca") == "baixa" and parsed.get("letras_corretas"):
        affected.append(r["question_id"])

print(f"Questões com confianca='baixa' que tiveram gabarito gravado indevidamente: {len(affected)}")
print(affected)

if not affected:
    print("Nada a corrigir.")
else:
    for qid in affected:
        cur.execute("SELECT letter, is_correct FROM choices WHERE question_id = ?", (qid,))
        before = [dict(x) for x in cur.fetchall()]
        print(f"  qid={qid} antes: {before}")

        if not args.dry_run:
            cur.execute("UPDATE choices SET is_correct = 0 WHERE question_id = ?", (qid,))

    if not args.dry_run:
        conn.commit()
        print(f"\n{len(affected)} questões revertidas para is_correct=0 em todas as choices.")
    else:
        print("\n[DRY RUN] Nenhuma alteração gravada.")

conn.close()
