from __future__ import annotations

import json
from pathlib import Path

from parser.database import Database


OUT_DIR = Path("app/public/data")
EXAMS_DIR = OUT_DIR / "exams"


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
        )


def export_subjects(db: Database):
    rows = db.execute(
        """
        SELECT
            subject,
            code,
            COUNT(*) AS exams
        FROM exams
        WHERE phase IN ('F1', 'F2')
        GROUP BY subject, code
        ORDER BY subject
        """
    ).fetchall()

    payload = [dict(row) for row in rows]

    write_json(
        OUT_DIR / "subjects.json",
        payload,
    )

    return len(payload)


def export_exams_index(db: Database):
    rows = db.execute(
        """
        SELECT
            id,
            exam_key,
            subject,
            code,
            year,
            phase
        FROM exams
        WHERE phase IN ('F1', 'F2')
        ORDER BY year DESC, subject, phase
        """
    ).fetchall()

    payload = [dict(row) for row in rows]

    write_json(
        OUT_DIR / "exams.json",
        payload,
    )

    return payload


def export_exam(db: Database, exam):
    questions = db.execute(
        """
        SELECT
            q.id,
            q.question_number,
            q.question_type,
            q.statement,
            q.topic,
            q.subtopic,
            q.difficulty,
            q.bloom_level,
            q.estimated_minutes,
            g.group_name,
            qc.title AS context_title,
            qc.raw_text AS context_text,
            cr.criteria_text,
            cr.official_answer,
            cr.max_points,
            ac.response_json AS ai_json
        FROM questions q
        LEFT JOIN groups_table g
            ON g.id = q.group_id
        LEFT JOIN question_contexts qc
            ON qc.id = q.context_id
        LEFT JOIN criteria cr
            ON cr.question_id = q.id
        LEFT JOIN ai_cache ac
            ON ac.question_id = q.id
        WHERE q.exam_id = ?
        ORDER BY q.id
        """,
        (exam["id"],),
    ).fetchall()

    exported_questions = []

    for question in questions:
        choices = db.execute(
            """
            SELECT
                id,
                letter,
                text,
                is_correct
            FROM choices
            WHERE question_id = ?
            ORDER BY letter
            """,
            (question["id"],),
        ).fetchall()

        ai_payload = None

        if question["ai_json"]:
            try:
                ai_payload = json.loads(question["ai_json"])
            except json.JSONDecodeError:
                ai_payload = None

        exported_questions.append(
            {
                "id": question["id"],
                "number": question["question_number"],
                "group": question["group_name"],
                "type": question["question_type"],
                "statement": question["statement"],
                "choices": [dict(choice) for choice in choices],
                "context": {
                    "title": question["context_title"],
                    "text": question["context_text"],
                },
                "correction": {
                    "criteria": question["criteria_text"],
                    "official_answer": question["official_answer"],
                    "max_points": question["max_points"],
                    "ai": ai_payload,
                },
                "learning": {
                    "topic": question["topic"],
                    "subtopic": question["subtopic"],
                    "difficulty": question["difficulty"],
                    "bloom": question["bloom_level"],
                    "estimated_minutes": question["estimated_minutes"],
                },
            }
        )

    payload = {
        "exam": dict(exam),
        "questions": exported_questions,
    }

    write_json(
        EXAMS_DIR / f"{exam['id']}.json",
        payload,
    )

    return len(exported_questions)


def main():
    db = Database()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EXAMS_DIR.mkdir(parents=True, exist_ok=True)

    subjects_count = export_subjects(db)
    exams = export_exams_index(db)

    total_questions = 0

    for exam in exams:
        total_questions += export_exam(db, exam)

    db.close()

    print()
    print("=" * 60)
    print("EXPORT STATIC SITE DATA")
    print("=" * 60)
    print(f"Subjects exported....: {subjects_count}")
    print(f"Exams exported.......: {len(exams)}")
    print(f"Questions exported...: {total_questions}")
    print(f"Output...............: {OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()