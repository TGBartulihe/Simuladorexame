from __future__ import annotations

import json

from parser.database import Database
from parser.models import Question


class DatabaseWriter:

    def __init__(self):

        self.db = Database()

    def save_questions(
        self,
        questions: list[Question],
    ) -> None:

        sql = """
        INSERT INTO question_blocks(

            exam_id,

            group_name,

            question_number,

            raw_statement,

            raw_criteria,

            status,

            updated_at

        )

        VALUES(

            ?,?,?,?,?,?,
            CURRENT_TIMESTAMP

        )

        ON CONFLICT(

            exam_id,

            group_name,

            question_number

        )

        DO UPDATE SET

            raw_statement = excluded.raw_statement,

            raw_criteria = excluded.raw_criteria,

            status='pending',

            updated_at=CURRENT_TIMESTAMP
        """

        rows = []

        for question in questions:

            rows.append(

                (

                    question.exam_id,

                    question.group,

                    question.number,

                    question.statement,

                    question.criteria,

                    "pending",

                )

            )

        self.db.executemany(
            sql,
            rows,
        )

        self.db.commit()

    def save_ai_json(
        self,
        exam_id: int,
        question_number: str,
        payload: dict,
    ):

        sql = """
        INSERT INTO ai_question_cache(

            exam_id,

            question_number,

            json

        )

        VALUES(

            ?,?,?

        )

        ON CONFLICT(

            exam_id,

            question_number

        )

        DO UPDATE SET

            json = excluded.json
        """

        self.db.execute(

            sql,

            (

                exam_id,

                question_number,

                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ),

            ),

        )

        self.db.commit()