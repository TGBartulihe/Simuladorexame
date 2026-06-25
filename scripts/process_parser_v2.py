from __future__ import annotations

from rich.progress import track

from parser.database import Database
from parser.database.schema import create_schema
from parser.parse.pipeline import ParserPipeline


def fetch_exams(db: Database):
    return db.execute(
        """
        SELECT
            e.id,
            e.exam_key,
            e.subject,
            e.year,
            e.phase,
            ex.extracted_text AS exam_text,
            cc.extracted_text AS criteria_text
        FROM exams e
        JOIN documents ex
            ON ex.id = e.exam_document_id
        LEFT JOIN documents cc
            ON cc.id = e.criteria_document_id
        WHERE e.phase IN ('F1', 'F2')
        ORDER BY
            e.year DESC,
            e.subject,
            e.phase
        """
    ).fetchall()


def clear_v2_tables(db: Database):
    tables = [
        "question_skills",
        "ai_cache",
        "student_answers",
        "student_attempts",
        "student_statistics",
        "choices",
        "criteria",
        "images",
        "tables",
        "questions",
        "question_contexts",
        "groups_table",
    ]

    for table in tables:
        db.execute(f"DELETE FROM {table}")

    db.commit()


def main():
    db = Database()

    create_schema(db.connection)

    clear_v2_tables(db)

    exams = fetch_exams(db)

    pipeline = ParserPipeline()

    total_questions = 0
    processed_exams = 0
    failed_exams = 0

    for exam in track(exams, description="Parser v2"):
        try:
            saved = pipeline.process_exam(
                exam_id=exam["id"],
                exam_text=exam["exam_text"] or "",
                criteria_text=exam["criteria_text"] or "",
            )

            total_questions += len(saved)
            processed_exams += 1

        except Exception as exc:
            failed_exams += 1
            print(f"[ERRO] {exam['exam_key']} | {exc}")

    pipeline.close()
    db.close()

    print()
    print("=" * 60)
    print("Parser v2 finalizado")
    print("=" * 60)
    print(f"Exames processados....: {processed_exams}")
    print(f"Exames com erro.......: {failed_exams}")
    print(f"Questões criadas......: {total_questions}")
    print("=" * 60)


if __name__ == "__main__":
    main()