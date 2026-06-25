from __future__ import annotations

import re

from parser.models import Group, Question
from parser.utils.extract_choices import extract_choices


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


MIN_SIZE = 120


class QuestionParser:
    def parse(
        self,
        exam_id: int,
        groups: list[Group],
    ) -> list[Question]:
        questions: list[Question] = []

        for group in groups:
            questions.extend(
                self._parse_group(
                    exam_id=exam_id,
                    group=group,
                )
            )

        return questions

    def _parse_group(
        self,
        exam_id: int,
        group: Group,
    ) -> list[Question]:
        matches = list(
            QUESTION_PATTERN.finditer(group.text)
        )

        if not matches:
            return []

        result: list[Question] = []

        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(group.text)

            raw = group.text[start:end].strip()

            if not self._is_valid_question(raw):
                continue

            statement, choices = extract_choices(raw)

            metadata = {
                "question_type": self.detect_type(statement, choices),
                "difficulty": None,
                "topic": None,
                "subtopic": None,
                "bloom": None,
                "estimated_minutes": None,
                "official_answer": None,
                "max_points": None,
            }

            result.append(
                Question(
                    exam_id=exam_id,
                    group=group.name,
                    number=match.group(1),
                    statement=statement,
                    choices=choices,
                    metadata=metadata,
                )
            )

        return result

    @staticmethod
    def _is_valid_question(block: str) -> bool:
        if len(block) < MIN_SIZE:
            return False

        first = block[:120].lower()

        if "página" in first:
            return False

        if first.startswith("figura"):
            return False

        if first.startswith("gráfico"):
            return False

        if first.startswith("tabela"):
            return False

        return True

    @staticmethod
    def detect_type(
        statement: str,
        choices: list[dict],
    ) -> str:
        if choices:
            return "multiple_choice"

        lower = statement.lower()

        if "justifique" in lower or "explique" in lower:
            return "essay"

        if "calcule" in lower or "determine" in lower:
            return "calculation"

        if "complete" in lower:
            return "completion"

        if "relacione" in lower or "associe" in lower:
            return "matching"

        if "ordene" in lower:
            return "ordering"

        return "open"