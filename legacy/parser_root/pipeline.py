from __future__ import annotations

from parser.clean_text import clean_text
from parser.split_pages import split_pages
from parser.parse_groups import parse_groups
from parser.parse_questions import parse_questions
from parser.parse_criteria import parse_criteria
from parser.match_questions import match_questions
from parser.database_writer import DatabaseWriter


class ParserPipeline:

    def __init__(self):

        self.writer = DatabaseWriter()

    def process_exam(

        self,

        exam_id: int,

        exam_text: str,

        criteria_text: str,

    ):

        exam_text = clean_text(exam_text)

        criteria_text = clean_text(criteria_text)

        exam_pages = split_pages(exam_text)

        criteria_pages = split_pages(criteria_text)

        groups = parse_groups(

            exam_id,

            exam_pages,

        )

        questions = parse_questions(

            exam_id,

            groups,

        )

        criteria = parse_criteria(

            criteria_pages,

        )

        questions = match_questions(

            questions,

            criteria,

        )

        self.writer.save_questions(

            questions,

        )

        return questions