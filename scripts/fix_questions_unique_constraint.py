"""
fix_questions_unique_constraint.py — migração pontual (não faz parte do
pipeline normal, roda uma vez só).

BUG ENCONTRADO: a constraint `UNIQUE(exam_id, question_number)` em
`questions` não inclui `group_id`. Como cada exame tem 3 grupos (GRUPO
I, II, III) e a numeração de questão REINICIA em cada grupo (GRUPO I
tem questões 1-20, GRUPO II tem questões 1-3, GRUPO III tem questões
1-4), o `INSERT ... ON CONFLICT(exam_id, question_number) DO UPDATE`
em `repository.py` fazia cada grupo processado depois SOBRESCREVER as
questões de número igual do grupo processado antes.

Resultado real observado: um exame que deveria ter 34 questões (GRUPO
I: 20, GRUPO II: 8, GRUPO III: 4 — mais 2 subitens 15.1/15.2) ficou só
com 22 — exatamente as do GRUPO I (1-20) mais os subitens, porque as
questões 1-3 do GRUPO II e 1-4 do GRUPO III, com numeração igual à de
questões do GRUPO I, foram perdidas no caminho (sobrescritas, ou a
sobrescrita aconteceu na direção oposta dependendo da ordem de
inserção — o ponto é que o conflito existe e descarta dados).

Esta migração:
  1. Recria o índice único incluindo group_id.
  2. Corrige a query de INSERT em repository.py para casar com o novo
     índice (isso está em parse_groups_corrigido... não, está em
     repository.py — ver arquivo separado `repository_corrigido.py`
     neste mesmo pacote).

IMPORTANTE: depois de rodar esta migração, é OBRIGATÓRIO reprocessar
(`python -m scripts.process_parser_v2`) — a migração só corrige a
estrutura para o futuro, não recupera as questões já perdidas pela
sobrescrita anterior (esse dado já não existe mais no banco).

Uso:
    python scripts/fix_questions_unique_constraint.py --db database/simuladorexame.db
"""
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
cur = conn.cursor()

print("Índices atuais em 'questions':")
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='questions'")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\nRecriando idx_questions_unique para incluir group_id...")
cur.execute("DROP INDEX IF EXISTS idx_questions_unique")
cur.execute(
    "CREATE UNIQUE INDEX idx_questions_unique ON questions(exam_id, group_id, question_number)"
)
conn.commit()

print("Índice recriado com sucesso.")
print("\nÍndices em 'questions' depois da migração:")
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='questions'")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print(
    "\nLEMBRETE: rode 'python -m scripts.process_parser_v2' agora para "
    "reprocessar com a constraint corrigida — os dados perdidos pela "
    "sobrescrita anterior não voltam sozinhos, precisam ser regravados."
)

conn.close()
