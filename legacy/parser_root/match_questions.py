from __future__ import annotations

from parser.models import Question


def match_questions(
    questions: list[Question],
    criteria: dict[str, str],
) -> list[Question]:

    for question in questions:

        if question.number in criteria:

            question.criteria = criteria[
                question.number
            ]

            continue

        #
        # fallback
        #

        if "." in question.number:

            parent = question.number.split(".")[0]

            if parent in criteria:

                question.criteria = criteria[parent]

    return questions