from __future__ import annotations

import re


CHOICE_PATTERN = re.compile(
    r"""
    \(\s*
    ([A-D])
    \s*\)

    (.*?)

    (?=

        \(\s*[A-D]\s*\)

        |

        $

    )
    """,
    re.DOTALL | re.VERBOSE,
)


def extract_choices(statement: str) -> tuple[str, list[str]]:

    matches = list(
        CHOICE_PATTERN.finditer(statement)
    )

    if not matches:
        return statement, []

    first = matches[0].start()

    question = statement[:first].strip()

    choices = []

    for match in matches:

        letter = match.group(1)

        text = " ".join(
            match.group(2).split()
        )

        choices.append(
            f"{letter}. {text}"
        )

    return question, choices