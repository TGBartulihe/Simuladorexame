from __future__ import annotations

import re

from parser.models import Page


ITEM_PATTERN = re.compile(
    r"""
    (?im)

    ^

    \s*

    (?:

        Item

        |

        Questão

        |

        Pergunta

    )?

    \s*

    (

        (?:[1-9][0-9]?)

        (?:\.[1-9][0-9]?)?

    )

    \b
    """,
    re.VERBOSE,
)


def parse_criteria(pages: list[Page]) -> dict[str, str]:

    text = "\n".join(page.text for page in pages)

    matches = list(ITEM_PATTERN.finditer(text))

    if not matches:
        return {}

    result: dict[str, str] = {}

    for index, match in enumerate(matches):

        start = match.start()

        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        number = match.group(1)

        block = text[start:end].strip()

        result[number] = block

    return result