from __future__ import annotations

from rich.progress import track

from parser.ai.question_analyzer import QuestionAnalyzer
from parser.database.repository import Repository


class ExamAnalyzer:

    def __init__(self):

        self.repository = Repository()

        self.question_analyzer = QuestionAnalyzer()

    # ===================================================

    def analyze_exam(

        self,

        exam_id,

    ):

        questions = self.repository.list_questions(
            exam_id
        )

        total = len(questions)

        processed = 0

        for question in track(

            questions,

            description=f"Exam {exam_id}",

        ):

            self.question_analyzer.analyze(
                question
            )

            processed += 1

        return {

            "processed": processed,

            "total": total,

        }

    # ===================================================

    def analyze_all(self):

        exams = self.repository.list_exams()

        summary = []

        for exam in exams:

            summary.append(

                self.analyze_exam(

                    exam["id"]

                )

            )

        return summary