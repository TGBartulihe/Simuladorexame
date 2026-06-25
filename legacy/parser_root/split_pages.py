from __future__ import annotations

import re

from parser.models import Page


PAGE_REGEX = re.compile(
    r"--- PAGE\s+(\d+)\s+---",
    re.IGNORECASE,
)


def split_pages(text: str) -> list[Page]:

    matches = list(PAGE_REGEX.finditer(text))

    if not matches:

        return [
            Page(
                number=1,
                text=text,
            )
        ]

    pages = []

    for index, match in enumerate(matches):

        start = match.end()

        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )

        pages.append(

            Page(

                number=int(match.group(1)),

                text=text[start:end].strip()

            )

        )

    return pages