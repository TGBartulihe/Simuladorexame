from __future__ import annotations

from parser.database.repository import Repository


class ExamService:

    def __init__(self):

        self.repository = Repository()

    # ======================================================

    def create_exam(

        self,

        exam_key: str,

        subject: str,

        code: str,

        year: int,

        phase: str,

        exam_document_id: int,

        criteria_document_id: int | None,

    ) -> int:

        return self.repository.insert_exam(

            exam_key=exam_key,

            subject=subject,

            code=code,

            year=year,

            phase=phase,

            exam_document_id=exam_document_id,

            criteria_document_id=criteria_document_id,

        )

    # ======================================================

    def list(self):

        return self.repository.list_exams()

    # ======================================================

    def get(self, exam_id: int):

        return self.repository.get_exam(exam_id)

    # ======================================================

    def questions(self, exam_id: int):

        return self.repository.list_questions(exam_id)

    # ======================================================

    def close(self):

        self.repository.close()