from __future__ import annotations

from dataclasses import dataclass

from parser.database.repository import Repository
from parser.services.exam_service import ExamService


@dataclass(slots=True)
class PendingExam:

    subject: str

    code: str

    year: int

    phase: str

    exam_document_id: int | None = None

    criteria_document_id: int | None = None


class ExamLibraryBuilder:

    def __init__(self):

        self.repository = Repository()

        self.exam_service = ExamService()

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def build(self):

        documents = self.repository.db.execute(
            """
            SELECT *

            FROM documents

            ORDER BY

                year DESC,

                subject,

                filename
            """
        ).fetchall()

        exams: dict[str, PendingExam] = {}

        for document in documents:

            if not document["subject"]:
                continue

            if not document["year"]:
                continue

            if not document["phase"]:
                continue

            key = self._exam_key(

                subject=document["subject"],

                code=document["code"],

                year=document["year"],

                phase=document["phase"],

            )

            if key not in exams:

                exams[key] = PendingExam(

                    subject=document["subject"],

                    code=document["code"],

                    year=document["year"],

                    phase=document["phase"],

                )

            exam = exams[key]

            if document["document_type"] == "exam":

                exam.exam_document_id = document["id"]

            elif document["document_type"] == "criteria":

                exam.criteria_document_id = document["id"]

        created = 0

        skipped = 0

        for key, exam in sorted(exams.items()):

            #
            # ignorar exames incompletos
            #

            if exam.exam_document_id is None:

                skipped += 1

                continue

            #
            # já existe?
            #

            exists = self.repository.db.execute(
                """
                SELECT id

                FROM exams

                WHERE exam_key=?
                """,
                (key,),
            ).fetchone()

            if exists:

                skipped += 1

                continue

            self.exam_service.create_exam(

                exam_key=key,

                subject=exam.subject,

                code=exam.code,

                year=exam.year,

                phase=exam.phase,

                exam_document_id=exam.exam_document_id,

                criteria_document_id=exam.criteria_document_id,

            )

            created += 1

        return {

            "created": created,

            "skipped": skipped,

            "total": len(exams),

        }

    # ==========================================================

    @staticmethod
    def _exam_key(

        subject: str,

        code: str,

        year: int,

        phase: str,

    ) -> str:

        return f"{year}-{code}-{phase}"

    # ==========================================================

    def close(self):

        self.exam_service.close()

        self.repository.close()