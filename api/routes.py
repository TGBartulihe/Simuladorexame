from __future__ import annotations

from fastapi import APIRouter, HTTPException

from parser.database import Database


router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/subjects")
def subjects():
    db = Database()

    rows = db.execute(
        """
        SELECT subject, code, COUNT(*) AS exams
        FROM exams
        WHERE phase IN ('F1', 'F2')
        GROUP BY subject, code
        ORDER BY subject
        """
    ).fetchall()

    db.close()

    return [dict(row) for row in rows]


@router.get("/exams")
def exams(subject: str | None = None):
    db = Database()

    if subject:
        rows = db.execute(
            """
            SELECT id, exam_key, subject, code, year, phase
            FROM exams
            WHERE phase IN ('F1', 'F2')
              AND subject = ?
            ORDER BY year DESC, phase
            """,
            (subject,),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT id, exam_key, subject, code, year, phase
            FROM exams
            WHERE phase IN ('F1', 'F2')
            ORDER BY year DESC, subject, phase
            """
        ).fetchall()

    db.close()

    return [dict(row) for row in rows]


@router.get("/exams/{exam_id}")
def exam_detail(exam_id: int):
    db = Database()

    exam = db.execute(
        """
        SELECT id, exam_key, subject, code, year, phase
        FROM exams
        WHERE id = ?
        """,
        (exam_id,),
    ).fetchone()

    if not exam:
        db.close()
        raise HTTPException(status_code=404, detail="Exam not found")

    questions = db.execute(
        """
        SELECT
            q.id,
            q.question_number,
            q.question_type,
            q.statement,
            q.context_id,
            qc.title AS context_title,
            qc.raw_text AS context_text,
            g.group_name
        FROM questions q
        LEFT JOIN groups_table g
            ON g.id = q.group_id
        LEFT JOIN question_contexts qc
            ON qc.id = q.context_id
        WHERE q.exam_id = ?
        ORDER BY q.id
        """,
        (exam_id,),
    ).fetchall()

    payload_questions = []

    for q in questions:
        choices = db.execute(
            """
            SELECT id, letter, text
            FROM choices
            WHERE question_id = ?
            ORDER BY letter
            """,
            (q["id"],),
        ).fetchall()

        payload_questions.append(
            {
                **dict(q),
                "choices": [dict(choice) for choice in choices],
            }
        )

    db.close()

    return {
        "exam": dict(exam),
        "questions": payload_questions,
    }


@router.post("/questions/{question_id}/check")
def check_answer(question_id: int, payload: dict):
    answer = payload.get("answer")

    db = Database()

    question = db.execute(
        """
        SELECT
            q.id,
            q.statement,
            q.question_type,
            c.criteria_text,
            c.official_answer
        FROM questions q
        LEFT JOIN criteria c
            ON c.question_id = q.id
        WHERE q.id = ?
        """,
        (question_id,),
    ).fetchone()

    if not question:
        db.close()
        raise HTTPException(status_code=404, detail="Question not found")

    choices = db.execute(
        """
        SELECT letter, text, is_correct
        FROM choices
        WHERE question_id = ?
        ORDER BY letter
        """,
        (question_id,),
    ).fetchall()

    correct = None

    for choice in choices:
        if choice["is_correct"]:
            correct = choice["letter"]

    db.close()

    return {
        "question_id": question_id,
        "submitted_answer": answer,
        "correct_answer": correct,
        "is_correct": bool(correct and answer == correct),
        "criteria": question["criteria_text"],
        "official_answer": question["official_answer"],
    }