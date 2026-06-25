from __future__ import annotations

import json
import sqlite3

from parser.database import Database
from parser.models import Question


class Repository:

    def __init__(self):

        self.db = Database()

    # ==========================================================
    # DOCUMENTS
    # ==========================================================

    def insert_document(
        self,
        filename,
        document_type,
        extracted_text,
        sha256=None,
        subject=None,
        year=None,
        phase=None,
        code=None,
    ):

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

    def get_document(self, document_id):

        return self.db.execute(
            """
            SELECT *

            FROM documents

            WHERE id=?
            """,
            (document_id,),
        ).fetchone()

    def get_document_by_filename(self, filename):

        return self.db.execute(
            """
            SELECT *

            FROM documents

            WHERE filename=?
            """,
            (filename,),
        ).fetchone()

    # ==========================================================
    # EXAMS
    # ==========================================================

    def insert_exam(

        self,

        exam_key,

        subject,

        code,

        year,

        phase,

        exam_document_id,

        criteria_document_id,

    ):

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

    def get_exam(self, exam_id):

        return self.db.execute(
            """
            SELECT *

            FROM exams

            WHERE id=?
            """,
            (exam_id,),
        ).fetchone()

    # ==========================================================
    # GROUPS
    # ==========================================================

    def insert_group(

        self,

        exam_id,

        group_name,

        display_order,

    ):

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

    # ==========================================================
    # QUESTIONS
    # ==========================================================

    def insert_question(

        self,

        exam_id,

        group_id,

        question: Question,

    ):

        cursor = self.db.execute(
            """
            INSERT INTO questions(

                exam_id,

                group_id,

                question_number,

                statement,

                question_type,

                difficulty,

                bloom_level,

                topic

            )

            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                exam_id,
                group_id,
                question.number,
                question.statement,
                question.metadata.get("question_type"),
                question.metadata.get("difficulty"),
                question.metadata.get("bloom"),
                question.metadata.get("topic"),
            ),
        )

        question_id = cursor.lastrowid

        #
        # alternativas
        #

        for choice in question.choices:

            self.insert_choice(

                question_id,

                choice["letter"],

                choice["text"],

                choice.get("correct", False),

            )

        #
        # critérios
        #

        if question.criteria:

            self.save_criteria(

                question_id,

                question.criteria,

            )

        self.db.commit()

        return question_id

    # ==========================================================
    # QUERY COMPLETA
    # ==========================================================

    def list_questions(

        self,

        exam_id,

    ):

        rows = self.db.execute(
            """
            SELECT

                q.id,

                q.exam_id,

                q.group_id,

                q.question_number,

                q.statement,

                q.question_type,

                q.max_points,

                q.difficulty,

                q.bloom_level,

                q.topic,

                c.criteria_text

            FROM questions q

            LEFT JOIN criteria c

                ON c.question_id=q.id

            WHERE

                q.exam_id=?

            ORDER BY

                q.question_number
            """,
            (exam_id,),
        ).fetchall()

        return rows

    def get_question(

        self,

        question_id,

    ):

        return self.db.execute(
            """
            SELECT

                q.*,

                c.criteria_text

            FROM questions q

            LEFT JOIN criteria c

                ON c.question_id=q.id

            WHERE

                q.id=?
            """,
            (question_id,),
        ).fetchone()

    # ==========================================================
    # CHOICES
    # ==========================================================

    def insert_choice(

        self,

        question_id,

        letter,

        text,

        correct=False,

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

    def list_choices(

        self,

        question_id,

    ):

        return self.db.execute(
            """
            SELECT *

            FROM choices

            WHERE question_id=?

            ORDER BY letter
            """,
            (question_id,),
        ).fetchall()

    # ==========================================================
    # CRITERIA
    # ==========================================================

    def save_criteria(

        self,

        question_id,

        criteria_text,

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

    # ==========================================================
    # AI CACHE
    # ==========================================================

    def save_ai_cache(

        self,

        question_id,

        model,

        prompt_hash,

        json_result,

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

        question_id,

    ):

        return self.db.execute(
            """
            SELECT *

            FROM ai_cache

            WHERE question_id=?
            """,
            (question_id,),
        ).fetchone()

    # ==========================================================

    def close(self):

        self.db.close()