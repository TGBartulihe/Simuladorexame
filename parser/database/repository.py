from __future__ import annotations

import sqlite3
from typing import Iterable, Optional

from parser.database import Database
from parser.models import (
    Document,
    Exam,
    Question,
)


class Repository:

    def __init__(self):

        self.db = Database()

    # ============================================================
    # DOCUMENTS
    # ============================================================

    def insert_document(
        self,
        filename: str,
        document_type: str,
        extracted_text: str,
        sha256: str | None = None,
        subject: str | None = None,
        year: int | None = None,
        phase: str | None = None,
        code: str | None = None,
    ) -> int:

        cursor = self.db.execute(
            """
            INSERT INTO documents(

                filename,
                sha256,
                document_type,
                subject,
                year,
                phase,
                code,
                extracted_text

            )

            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                filename,
                sha256,
                document_type,
                subject,
                year,
                phase,
                code,
                extracted_text,
            ),
        )

        self.db.commit()

        return cursor.lastrowid

    def get_document(
        self,
        document_id: int,
    ) -> Optional[sqlite3.Row]:

        return self.db.execute(
            """
            SELECT *
            FROM documents
            WHERE id=?
            """,
            (document_id,),
        ).fetchone()

    def get_document_by_filename(
        self,
        filename: str,
    ) -> Optional[sqlite3.Row]:

        return self.db.execute(
            """
            SELECT *
            FROM documents
            WHERE filename=?
            """,
            (filename,),
        ).fetchone()

    # ============================================================
    # EXAMS
    # ============================================================

    def insert_exam(

        self,

        exam_key: str,

        subject: str,

        code: str,

        year: int,

        phase: str,

        exam_document_id: int,

        criteria_document_id: int | None,

    ) -> int:

        cursor = self.db.execute(
            """
            INSERT INTO exams(

                exam_key,

                subject,

                code,

                year,

                phase,

                exam_document_id,

                criteria_document_id

            )

            VALUES(?,?,?,?,?,?,?)
            """,
            (
                exam_key,
                subject,
                code,
                year,
                phase,
                exam_document_id,
                criteria_document_id,
            ),
        )

        self.db.commit()

        return cursor.lastrowid

    def list_exams(self):

        return self.db.execute(
            """
            SELECT *

            FROM exams

            ORDER BY

                year DESC,

                subject,

                phase
            """
        ).fetchall()

    def get_exam(
        self,
        exam_id: int,
    ):

        return self.db.execute(
            """
            SELECT *

            FROM exams

            WHERE id=?
            """,
            (exam_id,),
        ).fetchone()

    # ============================================================
    # GROUPS
    # ============================================================

    def insert_group(

        self,

        exam_id: int,

        group_name: str,

        display_order: int,

    ) -> int:

        cursor = self.db.execute(
            """
            INSERT INTO groups_table(

                exam_id,

                group_name,

                display_order

            )

            VALUES(?,?,?)
            """,
            (
                exam_id,
                group_name,
                display_order,
            ),
        )

        self.db.commit()

        return cursor.lastrowid

    # ============================================================
    # QUESTIONS
    # ============================================================

    def insert_question(

        self,

        exam_id: int,

        group_id: int | None,

        question: Question,

    ) -> int:

        cursor = self.db.execute(
            """
            INSERT INTO questions(

                exam_id,

                group_id,

                question_number,

                statement

            )

            VALUES(?,?,?,?)
            """,
            (
                exam_id,
                group_id,
                question.number,
                question.statement,
            ),
        )

        self.db.commit()

        return cursor.lastrowid

    def list_questions(
        self,
        exam_id: int,
    ):

        return self.db.execute(
            """
            SELECT *

            FROM questions

            WHERE exam_id=?

            ORDER BY id
            """,
            (exam_id,),
        ).fetchall()

    # ============================================================
    # CHOICES
    # ============================================================

    def insert_choice(

        self,

        question_id: int,

        letter: str,

        text: str,

        correct: bool = False,

    ):

        self.db.execute(
            """
            INSERT INTO choices(

                question_id,

                letter,

                text,

                is_correct

            )

            VALUES(?,?,?,?)
            """,
            (
                question_id,
                letter,
                text,
                int(correct),
            ),
        )

    # ============================================================
    # CRITERIA
    # ============================================================

    def save_criteria(

        self,

        question_id: int,

        criteria_text: str,

    ):

        self.db.execute(
            """
            INSERT INTO criteria(

                question_id,

                criteria_text

            )

            VALUES(?,?)

            ON CONFLICT(question_id)

            DO UPDATE SET

            criteria_text=excluded.criteria_text
            """,
            (
                question_id,
                criteria_text,
            ),
        )

        self.db.commit()

    # ============================================================
    # AI CACHE
    # ============================================================

    def save_ai_cache(

        self,

        question_id: int,

        model: str,

        prompt_hash: str,

        json_result: str,

    ):

        self.db.execute(
            """
            INSERT INTO ai_cache(

                question_id,

                model,

                prompt_hash,

                response_json

            )

            VALUES(?,?,?,?)

            ON CONFLICT(question_id)

            DO UPDATE SET

                model=excluded.model,

                prompt_hash=excluded.prompt_hash,

                response_json=excluded.response_json
            """,
            (
                question_id,
                model,
                prompt_hash,
                json_result,
            ),
        )

        self.db.commit()

    def get_ai_cache(
        self,
        question_id: int,
    ):

        return self.db.execute(
            """
            SELECT *

            FROM ai_cache

            WHERE question_id=?
            """,
            (question_id,),
        ).fetchone()

    # ============================================================

    def close(self):

        self.db.close()