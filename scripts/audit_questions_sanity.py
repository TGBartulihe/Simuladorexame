"""
audit_questions_sanity.py — auditoria pós-reprocessamento (não faz
parte do pipeline normal, roda manualmente depois de
process_parser_v2). Em vez de eu prever um número exato e você
verificar manualmente exame por exame, este script aplica checagens
automáticas sobre TODOS os exames de uma vez, sinalizando padrões
suspeitos para revisão -- sem depender de eu adivinhar certo.

Checagens:
  1. Exames com poucas questões (< 15) -- pode indicar perda de dados.
  2. Exames com muitas questões (> 35) -- pode indicar fragmentos
     espúrios não filtrados (ex: uma grade de opções que escapou).
  3. Sequências de question_number com saltos suspeitos dentro do
     mesmo group_id (ex: 1,2,3,7,8 -- sugere que 4,5,6 foram perdidos
     ou nunca deveriam ter existido).
  4. Statements muito curtos (< 150 chars) ainda presentes -- candidatos
     a fragmento espúrio que passou pelo filtro.
  5. group_id NULL em alguma questão (não deveria acontecer).

Isto não substitui uma revisão manual de amostra, mas reduz
drasticamente onde procurar.

Uso:
    python scripts/audit_questions_sanity.py --db database/simuladorexame.db
"""
import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--min-questions", type=int, default=15)
parser.add_argument("--max-questions", type=int, default=35)
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("1. Exames com contagem de questões muito diferente da média da MESMA disciplina")
print("=" * 70)
print(
    "Nota: a versão anterior deste script usava um limite fixo [15, 35] "
    "para todas as disciplinas, sem base real — Português, por natureza, "
    "tem menos itens (mais questões de desenvolvimento longas) que "
    "Biologia/Física (mais itens objetivos). Esta versão compara cada "
    "exame com a MÉDIA DA PRÓPRIA disciplina, o que é mais confiável."
)
cur.execute(
    """
    SELECT e.subject, e.exam_key, COUNT(q.id) as total
    FROM exams e
    JOIN questions q ON q.exam_id = e.id
    GROUP BY e.id
    """
)
all_counts = cur.fetchall()

by_subject: dict[str, list[tuple[str, int]]] = {}
for r in all_counts:
    by_subject.setdefault(r["subject"], []).append((r["exam_key"], r["total"]))

suspicious_count = []
for subject, exams in by_subject.items():
    totals = [t for _, t in exams]
    avg = sum(totals) / len(totals)
    # desvio simples sem numpy: raiz da variância
    variance = sum((t - avg) ** 2 for t in totals) / len(totals)
    stdev = variance ** 0.5
    threshold = max(stdev * 2, 3)  # pelo menos 3 questões de margem
    for exam_key, total in exams:
        if abs(total - avg) > threshold:
            suspicious_count.append((exam_key, subject, total, round(avg, 1)))

suspicious_count.sort(key=lambda x: x[2])
print(f"\n{len(suspicious_count)} exames com desvio >2 desvios-padrão da média da disciplina:")
for exam_key, subject, total, avg in suspicious_count:
    print(f"  {exam_key} ({subject}): {total} questões (média da disciplina: {avg})")

print()
print("=" * 70)
print("2. group_id NULL (não deveria existir)")
print("=" * 70)
cur.execute("SELECT COUNT(*) FROM questions WHERE group_id IS NULL")
null_group_count = cur.fetchone()[0]
print(f"Questões com group_id NULL: {null_group_count}")

print()
print("=" * 70)
print("3. Saltos suspeitos na numeração dentro do mesmo (exam_id, group_id)")
print("=" * 70)
cur.execute(
    """
    SELECT exam_id, group_id, question_number
    FROM questions
    WHERE question_number NOT LIKE '%.%'
    ORDER BY exam_id, group_id, CAST(question_number AS INTEGER)
    """
)
rows = cur.fetchall()
by_group: dict[tuple, list[int]] = {}
for r in rows:
    key = (r["exam_id"], r["group_id"])
    by_group.setdefault(key, []).append(int(r["question_number"]))

gap_issues = []
for (exam_id, group_id), numbers in by_group.items():
    numbers_sorted = sorted(numbers)
    for i in range(1, len(numbers_sorted)):
        gap = numbers_sorted[i] - numbers_sorted[i - 1]
        if gap > 1:
            gap_issues.append((exam_id, group_id, numbers_sorted[i - 1], numbers_sorted[i]))

print(f"{len(gap_issues)} saltos encontrados (mostrando até 20):")
for exam_id, group_id, before, after in gap_issues[:20]:
    cur.execute("SELECT exam_key FROM exams WHERE id = ?", (exam_id,))
    exam_key = cur.fetchone()[0]
    print(f"  {exam_key} group_id={group_id}: salto de {before} para {after}")

print()
print("=" * 70)
print("4. Statements curtos (< 150 chars) — CONTEXTO IMPORTANTE")
print("=" * 70)
cur.execute("SELECT COUNT(*) FROM questions WHERE LENGTH(statement) < 150")
short_count = cur.fetchone()[0]
print(f"Total: {short_count}")
print(
    "AVISO: esta contagem NÃO é, por si só, sinal de problema. Confirmado "
    "manualmente (ver conversa) que questões de escolha múltipla em Biologia "
    "e Geologia / Física e Química A costumam ter enunciado curto e "
    "incompleto de propósito — a frase só fica completa quando junta com "
    "cada alternativa (ex: '1. Ao longo da falha de Ornach-Nal, ocorrem "
    "predominantemente' + '(A) deslizamento lateral...'). Isso é o FORMATO "
    "real da questão, não um truncamento. Só investigue isto se o "
    "question_type NÃO for multiple_choice (um statement curto numa "
    "questão aberta/essay é mais suspeito, já que essas costumam ter "
    "enunciados mais longos)."
)
print()
cur.execute(
    """
    SELECT e.exam_key, q.question_number, q.question_type, LENGTH(q.statement) as len, q.statement
    FROM questions q JOIN exams e ON e.id = q.exam_id
    WHERE LENGTH(q.statement) < 150 AND q.question_type != 'multiple_choice'
    ORDER BY len ASC LIMIT 15
    """
)
non_mc_short = cur.fetchall()
print(f"Statements curtos que NÃO são multiple_choice (mais suspeitos): {len(non_mc_short)}")
for r in non_mc_short:
    preview = (r["statement"] or "")[:70].replace("\n", " ")
    print(f"  {r['exam_key']} num={r['question_number']} tipo={r['question_type']} len={r['len']}: {preview!r}")

print()
print("=" * 70)
print("RESUMO")
print("=" * 70)
cur.execute("SELECT COUNT(DISTINCT exam_id) FROM questions")
total_exams = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM questions")
total_questions = cur.fetchone()[0]
print(f"Total de exames com questões: {total_exams}")
print(f"Total de questões: {total_questions}")
print(f"Média de questões por exame: {total_questions/total_exams:.1f}")
print()
print(f"Exames fora da faixa esperada: {len(suspicious_count)}")
print(f"group_id NULL: {null_group_count}")
print(f"Saltos de numeração suspeitos: {len(gap_issues)}")
print(f"Statements curtos: {short_count}")
