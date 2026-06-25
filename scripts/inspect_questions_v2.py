from __future__ import annotations

from parser.database import Database


def main():
    db = Database()

    total_exams = db.execute(
        """
        SELECT COUNT(*)
        FROM exams
        WHERE phase IN ('F1', 'F2')
        """
    ).fetchone()[0]

    total_questions = db.execute(
        """
        SELECT COUNT(*)
        FROM questions
        """
    ).fetchone()[0]

    total_choices = db.execute(
        """
        SELECT COUNT(*)
        FROM choices
        """
    ).fetchone()[0]

    total_criteria = db.execute(
        """
        SELECT COUNT(*)
        FROM criteria
        WHERE criteria_text IS NOT NULL
          AND length(criteria_text) > 0
        """
    ).fetchone()[0]

    by_subject = db.execute(
        """
        SELECT
            e.subject,
            COUNT(q.id) AS questions
        FROM exams e
        LEFT JOIN questions q
            ON q.exam_id = e.id
        WHERE e.phase IN ('F1', 'F2')
        GROUP BY e.subject
        ORDER BY e.subject
        """
    ).fetchall()

    by_type = db.execute(
        """
        SELECT
            COALESCE(question_type, 'unknown') AS type,
            COUNT(*) AS total
        FROM questions
        GROUP BY COALESCE(question_type, 'unknown')
        ORDER BY total DESC
        """
    ).fetchall()

    missing_criteria = db.execute(
        """
        SELECT
            e.exam_key,
            e.subject,
            q.question_number,
            substr(q.statement, 1, 180)
        FROM questions q
        JOIN exams e
            ON e.id = q.exam_id
        LEFT JOIN criteria c
            ON c.question_id = q.id
        WHERE c.id IS NULL
           OR c.criteria_text IS NULL
           OR length(c.criteria_text) = 0
        ORDER BY e.year DESC, e.subject, e.phase, q.id
        LIMIT 20
        """
    ).fetchall()

    samples = db.execute(
        """
        SELECT
            e.exam_key,
            e.subject,
            g.group_name,
            q.question_number,
            q.question_type,
            length(q.statement) AS statement_len,
            (
                SELECT COUNT(*)
                FROM choices c
                WHERE c.question_id = q.id
            ) AS choices,
            CASE
                WHEN cr.criteria_text IS NULL THEN 0
                ELSE length(cr.criteria_text)
            END AS criteria_len,
            substr(q.statement, 1, 220)
        FROM questions q
        JOIN exams e
            ON e.id = q.exam_id
        LEFT JOIN groups_table g
            ON g.id = q.group_id
        LEFT JOIN criteria cr
            ON cr.question_id = q.id
        ORDER BY e.year DESC, e.subject, e.phase, q.id
        LIMIT 25
        """
    ).fetchall()

    print()
    print("=" * 60)
    print("INSPEÇÃO QUESTIONS V2")
    print("=" * 60)
    print(f"Exames F1/F2...........: {total_exams}")
    print(f"Questões...............: {total_questions}")
    print(f"Choices................: {total_choices}")
    print(f"Questões com critérios.: {total_criteria}")

    print()
    print("Por disciplina:")
    for row in by_subject:
        print(f"- {row['subject']}: {row['questions']}")

    print()
    print("Por tipo:")
    for row in by_type:
        print(f"- {row['type']}: {row['total']}")

    print()
    print("Amostras:")
    for row in samples:
        print("-" * 60)
        print(
            f"{row['exam_key']} | {row['subject']} | "
            f"{row['group_name']} | Q{row['question_number']} | "
            f"{row['question_type']} | choices={row['choices']} | "
            f"criteria={row['criteria_len']}"
        )
        print(row[8])

    print()
    print("Sem critérios, amostra:")
    for row in missing_criteria:
        print("-" * 60)
        print(f"{row['exam_key']} | {row['subject']} | Q{row['question_number']}")
        print(row[3])

    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()