"""
inspect_exam_25_pipeline.py — utilitário de diagnóstico (não faz parte
do pipeline). Roda EXATAMENTE o mesmo código que process_parser_v2.py
roda (via ParserPipeline.process_exam), mas só para o exame
2025-702-F1, e imprime o resultado intermediário passo a passo — para
comparar com o que o teste piloto (que chama os módulos diretamente,
sem passar por Repository/banco) mostrou.

Isso existe porque process_exam() grava direto no banco via
Repository — não dá para só "rodar e ver", preciso instrumentar.

Uso:
    python scripts/inspect_exam_25_pipeline.py --db database/simuladorexame.db
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser.utils.clean_text import clean_text
from parser.utils.split_pages import split_pages
from parser.parse.parse_groups import parse_groups
from parser.parse.parse_questions import QuestionParser
from parser.utils.match_questions import match_questions
from parser.parse.parse_criteria import parse_criteria

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute(
    """
    SELECT e.id, e.exam_key, ex.extracted_text AS exam_text, cc.extracted_text AS criteria_text
    FROM exams e
    JOIN documents ex ON ex.id = e.exam_document_id
    LEFT JOIN documents cc ON cc.id = e.criteria_document_id
    WHERE e.exam_key = '2025-702-F1'
    """
)
row = cur.fetchone()
if not row:
    print("Exame 2025-702-F1 não encontrado.")
    sys.exit(1)

print(f"exam_id real usado pelo pipeline: {row['id']}")
print(f"exam_document_id aponta para o documento correto? (deveria ser id=61, V1)")
print()

exam_text = clean_text(row["exam_text"] or "")
criteria_text = clean_text(row["criteria_text"] or "")

exam_pages = split_pages(exam_text)
criteria_pages = split_pages(criteria_text)

groups = parse_groups(exam_id=row["id"], pages=exam_pages)
print(f"Grupos: {[g.name for g in groups]}")

question_parser = QuestionParser()
questions = question_parser.parse(exam_id=row["id"], groups=groups)
print(f"Questões (via pipeline real): {len(questions)}")
for q in questions:
    preview = q.statement.strip().replace("\n", " ")[:60]
    print(f"  [{q.number:>6}] {preview}")

criteria = parse_criteria(criteria_pages)
print(f"\nCritérios: {len(criteria)}")

matched = match_questions(questions=questions, criteria=criteria)
print(f"\nDepois de match_questions: {len(matched)} questões")
for q in matched:
    preview = q.statement.strip().replace("\n", " ")[:60]
    print(f"  [{q.number:>6}] {preview}")
