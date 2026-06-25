from __future__ import annotations

import json

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
            ORDER BY year DESC, subject, phase
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
        context_text=None,
    ):

        cursor = self.db.execute(
            """
            INSERT INTO groups_table(
                exam_id,
                group_name,
                display_order,
                context_text
            )
            VALUES(?,?,?,?)
            """,
            (
                exam_id,
                group_name,
                display_order,
                context_text,
            ),
        )

        self.db.commit()

        return cursor.lastrowid

    def get_group_by_name(self, exam_id, group_name):

        return self.db.execute(
            """
            SELECT *
            FROM groups_table
            WHERE exam_id=? AND group_name=?
            """,
            (
                exam_id,
                group_name,
            ),
        ).fetchone()

    # ==========================================================
    # CONTEXTS
    # ==========================================================

    def insert_context(
        self,
        exam_id,
        group_id,
        context_key,
        title,
        raw_text,
    ):

        cursor = self.db.execute(
            """
            INSERT INTO question_contexts(
                exam_id,
                group_id,
                context_key,
                title,
                raw_text
            )
            VALUES(?,?,?,?,?)
            ON CONFLICT(exam_id, context_key)
            DO UPDATE SET
                group_id=excluded.group_id,
                title=excluded.title,
                raw_text=excluded.raw_text
            """,
            (
                exam_id,
                group_id,
                context_key,
                title,
                raw_text,
            ),
        )

        self.db.commit()

        if cursor.lastrowid:
            return cursor.lastrowid

        row = self.db.execute(
            """
            SELECT id
            FROM question_contexts
            WHERE exam_id=? AND context_key=?
            """,
            (
                exam_id,
                context_key,
            ),
        ).fetchone()

        return row["id"]

    def get_context(self, context_id):

        return self.db.execute(
            """
            SELECT *
            FROM question_contexts
            WHERE id=?
            """,
            (context_id,),
        ).fetchone()

    # ==========================================================
    # QUESTIONS
    # ==========================================================

    def insert_question(
        self,
        exam_id,
        group_id,
        question: Question,
        context_id=None,
    ):

        cursor = self.db.execute(
            """
            INSERT INTO questions(
                exam_id,
                group_id,
                context_id,
                question_number,
                statement,
                question_type,
                difficulty,
                bloom_level,
                topic,
                subtopic,
                estimated_minutes,
                updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(exam_id, question_number)
            DO UPDATE SET
                group_id=excluded.group_id,
                context_id=excluded.context_id,
                statement=excluded.statement,
                question_type=excluded.question_type,
                difficulty=excluded.difficulty,
                bloom_level=excluded.bloom_level,
                topic=excluded.topic,
                subtopic=excluded.subtopic,
                estimated_minutes=excluded.estimated_minutes,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                exam_id,
                group_id,
                context_id,
                question.number,
                question.statement,
                question.metadata.get("question_type"),
                question.metadata.get("difficulty"),
                question.metadata.get("bloom"),
                question.metadata.get("topic"),
                question.metadata.get("subtopic"),
                question.metadata.get("estimated_minutes"),
            ),
        )

        self.db.commit()

        row = self.db.execute(
            """
            SELECT id
            FROM questions
            WHERE exam_id=? AND question_number=?
            """,
            (
                exam_id,
                question.number,
            ),
        ).fetchone()

        question_id = row["id"]

        self.delete_choices(question_id)

        for choice in question.choices:

            self.insert_choice(
                question_id,
                choice["letter"],
                choice["text"],
                choice.get("correct", False),
            )

        if question.criteria:

            self.save_criteria(
                question_id,
                question.criteria,
                question.metadata.get("max_points"),
                question.metadata.get("official_answer"),
            )

        self.db.commit()

        return question_id

    def list_questions(self, exam_id):

        return self.db.execute(
            """
            SELECT
                q.id,
                q.exam_id,
                q.group_id,
                q.context_id,
                q.question_number,
                q.statement,
                q.question_type,
                q.max_points,
                q.difficulty,
                q.bloom_level,
                q.topic,
                q.subtopic,
                q.estimated_minutes,
                c.criteria_text,
                c.official_answer,
                c.max_points AS criteria_max_points,
                qc.raw_text AS context_text,
                qc.title AS context_title
            FROM questions q
            LEFT JOIN criteria c
                ON c.question_id=q.id
            LEFT JOIN question_contexts qc
                ON qc.id=q.context_id
            WHERE q.exam_id=?
            ORDER BY q.id
            """,
            (exam_id,),
        ).fetchall()

    def get_question(self, question_id):

        return self.db.execute(
            """
            SELECT
                q.*,
                c.criteria_text,
                c.official_answer,
                c.max_points AS criteria_max_points,
                qc.raw_text AS context_text,
                qc.title AS context_title
            FROM questions q
            LEFT JOIN criteria c
                ON c.question_id=q.id
            LEFT JOIN question_contexts qc
                ON qc.id=q.context_id
            WHERE q.id=?
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
            ON CONFLICT(question_id, letter)
            DO UPDATE SET
                text=excluded.text,
                is_correct=excluded.is_correct
            """,
            (
                question_id,
                letter,
                text,
                int(correct),
            ),
        )

    def delete_choices(self, question_id):

        self.db.execute(
            """
            DELETE FROM choices
            WHERE question_id=?
            """,
            (question_id,),
        )

    def list_choices(self, question_id):

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
        max_points=None,
        official_answer=None,
    ):

        self.db.execute(
            """
            INSERT INTO criteria(
                question_id,
                criteria_text,
                max_points,
                official_answer
            )
            VALUES(?,?,?,?)
            ON CONFLICT(question_id)
            DO UPDATE SET
                criteria_text=excluded.criteria_text,
                max_points=excluded.max_points,
                official_answer=excluded.official_answer
            """,
            (
                question_id,
                criteria_text,
                max_points,
                official_answer,
            ),
        )

    # ==========================================================
    # TOPICS / SKILLS
    # ==========================================================

    def get_or_create_topic(self, subject, name, parent_id=None):

        row = self.db.execute(
            """
            SELECT id
            FROM topics
            WHERE subject=? AND name=?
            """,
            (
                subject,
                name,
            ),
        ).fetchone()

        if row:
            return row["id"]

        cursor = self.db.execute(
            """
            INSERT INTO topics(
                subject,
                name,
                parent_id
            )
            VALUES(?,?,?)
            """,
            (
                subject,
                name,
                parent_id,
            ),
        )

        self.db.commit()

        return cursor.lastrowid

    def get_or_create_skill(self, subject, name):

        row = self.db.execute(
            """
            SELECT id
            FROM skills
            WHERE subject=? AND name=?
            """,
            (
                subject,
                name,
            ),
        ).fetchone()

        if row:
            return row["id"]

        cursor = self.db.execute(
            """
            INSERT INTO skills(
                subject,
                name
            )
            VALUES(?,?)
            """,
            (
                subject,
                name,
            ),
        )

        self.db.commit()

        return cursor.lastrowid

    def link_question_skill(self, question_id, skill_id):

        self.db.execute(
            """
            INSERT OR IGNORE INTO question_skills(
                question_id,
                skill_id
            )
            VALUES(?,?)
            """,
            (
                question_id,
                skill_id,
            ),
        )

        self.db.commit()

    # ==========================================================
    # AI CACHE
    # ==========================================================

    def save_ai_cache(
        self,
        question_id,
        model,
        prompt_hash,
        json_result,
        prompt_version=None,
    ):

        self.db.execute(
            """
            INSERT INTO ai_cache(
                question_id,
                model,
                prompt_version,
                prompt_hash,
                response_json,
                updated_at
            )
            VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(question_id)
            DO UPDATE SET
                model=excluded.model,
                prompt_version=excluded.prompt_version,
                prompt_hash=excluded.prompt_hash,
                response_json=excluded.response_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                question_id,
                model,
                prompt_version,
                prompt_hash,
                json_result,
            ),
        )

        self.db.commit()

    def get_ai_cache(self, question_id):

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
    