from __future__ import annotations

import re

from parser.models import Group
from parser.models import Question


QUESTION_PATTERN = re.compile(
    r"""
    (?m)

    ^

    \s*

    (

        (?:[1-9][0-9]?)

        (?:\.[1-9][0-9]?)?

    )

    \.

    \s+
    """,
    re.VERBOSE,
)


PAGE_HEADER = re.compile(
    r"(?im)^Prova\s+\d+.*Página"
)


GRAPHIC_HEADER = re.compile(
    r"(?im)^Figura\s+\d+"
)


TABLE_HEADER = re.compile(
    r"(?im)^Tabela\s+\d+"
)


GRAPH_HEADER = re.compile(
    r"(?im)^Gráfico\s+\d+"
)


MIN_QUESTION_SIZE = 120


def _is_real_question(block: str) -> bool:

    if len(block) < MIN_QUESTION_SIZE:
        return False

    first = block[:120]

    if PAGE_HEADER.search(first):
        return False

    if GRAPHIC_HEADER.search(first):
        return False

    if TABLE_HEADER.search(first):
        return False

    if GRAPH_HEADER.search(first):
        return False

    return True


def parse_questions(
    exam_id: int,
    groups: list[Group],
) -> list[Question]:

    result: list[Question] = []

    for group in groups:

        matches = list(
            QUESTION_PATTERN.finditer(group.text)
        )

        if not matches:
            continue

        for index, match in enumerate(matches):

            start = match.start()

            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(group.text)
            )

            block = group.text[start:end].strip()

            if not _is_real_question(block):
                continue

            result.append(

                Question(

                    exam_id=exam_id,

                    group=group.name,

                    number=match.group(1),

                    statement=block,

                )

            )

    return result