from __future__ import annotations

from parser.clean_text import clean_text
from parser.split_pages import split_pages
from parser.parse_groups import parse_groups
from parser.parse_questions import parse_questions
from parser.parse_criteria import parse_criteria
from parser.parse.extract_contexts import extract_contexts
from parser.match_questions import match_questions
from parser.database.repository import Repository


class ParserPipeline:
    def __init__(self):
        self.repository = Repository()

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

        group_ids: dict[str, int] = {}

        for group in groups:
            group_ids[group.name] = self.repository.insert_group(
                exam_id=exam_id,
                group_name=group.name,
                display_order=group.order,
                context_text=None,
            )

        contexts = extract_contexts(groups)

        context_ids: dict[str, int] = {}

        for group_name, context in contexts.items():
            context_ids[group_name] = self.repository.insert_context(
                exam_id=exam_id,
                group_id=group_ids.get(group_name),
                context_key=context.key,
                title=context.title,
                raw_text=context.raw_text,
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

        saved = []

        for question in questions:
            group_id = group_ids.get(question.group)
            context_id = context_ids.get(question.group)

            question_id = self.repository.insert_question(
                exam_id=exam_id,
                group_id=group_id,
                question=question,
                context_id=context_id,
            )

            saved.append(question_id)

        return saved

    def close(self):
        self.repository.close()