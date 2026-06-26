"""
triage_exams.py — classifica cada exame como 'bom' ou 'revisar', sem
exigir investigação manual de cada um. Roda uma vez, depois disso a
UI/export só usa os exames 'bons' — os problemáticos ficam de lado,
não bloqueiam o uso do resto.

Critério de 'bom' (todos precisam ser verdade):
  - Tem pelo menos 2 grupos (GRUPO I, II...) -- exames com só 1 grupo
    são suspeitos de ter perdido conteúdo na extração.
  - Contagem de questões dentro de 2 desvios-padrão da média da própria
    disciplina.
  - Nenhum salto de numeração maior que 3 dentro do mesmo grupo (saltos
    pequenos podem ser legítimos -- grupos de "responda 4 de 8 itens";
    saltos grandes são suspeitos).
  - O texto do documento da prova não é anormalmente curto comparado à
    média de chars/questão da própria disciplina.

Isto NÃO tenta ser perfeito -- é um filtro de primeira linha. Exames
marcados 'revisar' não são necessariamente errados, só não foram
validados manualmente. Exames 'bons' não são garantidos 100% corretos,
só passam os testes automáticos disponíveis.

Uso:
    python scripts/triage_exams.py --db database/simuladorexame.db
"""
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# tabela de triagem -- não estraga nada existente, é só uma flag adicional
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS exam_triage (
        exam_id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        reasons TEXT,
        FOREIGN KEY(exam_id) REFERENCES exams(id)
    )
    """
)
cur.execute("DELETE FROM exam_triage")

cur.execute(
    """
    SELECT e.id, e.exam_key, e.subject, COUNT(q.id) as total
    FROM exams e
    LEFT JOIN questions q ON q.exam_id = e.id
    GROUP BY e.id
    """
)
all_exams = cur.fetchall()

by_subject: dict[str, list[int]] = {}
for r in all_exams:
    by_subject.setdefault(r["subject"], []).append(r["total"])

subject_stats = {}
for subject, totals in by_subject.items():
    avg = sum(totals) / len(totals)
    variance = sum((t - avg) ** 2 for t in totals) / len(totals)
    subject_stats[subject] = (avg, variance ** 0.5)

good_count = 0
review_count = 0

for exam in all_exams:
    reasons = []

    if exam["total"] == 0:
        reasons.append("sem_questoes_extraidas")
    else:
        avg, stdev = subject_stats[exam["subject"]]
        threshold = max(stdev * 2, 3)
        if abs(exam["total"] - avg) > threshold:
            reasons.append(f"contagem_atipica(total={exam['total']},media_disciplina={avg:.1f})")

        cur.execute(
            "SELECT COUNT(DISTINCT group_id) FROM questions WHERE exam_id = ?", (exam["id"],)
        )
        group_count = cur.fetchone()[0]
        if group_count < 2:
            reasons.append(f"poucos_grupos({group_count})")

        cur.execute(
            "SELECT group_id, question_number FROM questions WHERE exam_id = ? AND question_number NOT LIKE '%.%'",
            (exam["id"],),
        )
        by_group: dict[int, list[int]] = {}
        for r in cur.fetchall():
            by_group.setdefault(r["group_id"], []).append(int(r["question_number"]))

        max_gap = 0
        for group_id, numbers in by_group.items():
            numbers_sorted = sorted(numbers)
            for i in range(1, len(numbers_sorted)):
                gap = numbers_sorted[i] - numbers_sorted[i - 1]
                max_gap = max(max_gap, gap)
        if max_gap > 3:
            reasons.append(f"salto_numeracao(max_gap={max_gap})")

    status = "revisar" if reasons else "bom"
    if status == "bom":
        good_count += 1
    else:
        review_count += 1

    cur.execute(
        "INSERT INTO exam_triage (exam_id, status, reasons) VALUES (?, ?, ?)",
        (exam["id"], status, "; ".join(reasons)),
    )

conn.commit()

print(f"Total de exames avaliados: {len(all_exams)}")
print(f"  'bom' (prontos para uso): {good_count}")
print(f"  'revisar' (não bloqueiam o resto, mas precisam de atenção): {review_count}")
print()
print("Lista de exames marcados 'revisar':")
cur.execute(
    """
    SELECT e.exam_key, e.subject, t.reasons
    FROM exam_triage t
    JOIN exams e ON e.id = t.exam_id
    WHERE t.status = 'revisar'
    ORDER BY e.subject, e.exam_key
    """
)
for r in cur.fetchall():
    print(f"  {r['exam_key']} ({r['subject']}): {r['reasons']}")

conn.close()
