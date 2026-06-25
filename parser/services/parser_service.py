from __future__ import annotations

from parser.pipeline import ParserPipeline

from parser.services.exam_service import ExamService

from parser.services.document_service import DocumentService


class ParserService:

    def __init__(self):

        self.pipeline = ParserPipeline()

        self.exam_service = ExamService()

        self.document_service = DocumentService()

    # ======================================================

    def process_exam(

        self,

        exam_id: int,

        exam_text: str,

        criteria_text: str,

    ):

        return self.pipeline.process_exam(

            exam_id,

            exam_text,

            criteria_text,

        )

    # ======================================================

    def process_all(self):

        exams = self.exam_service.list()

        processed = 0

        for exam in exams:

            processed += 1

        return processed

    # ======================================================

    def close(self):

        self.exam_service.close()

        self.document_service.close()