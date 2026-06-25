from __future__ import annotations

import re

from parser.models import Group, Page


GROUP_PATTERN = re.compile(
    r"(?im)^\s*GRUPO\s+(I|II|III|IV|V)\s*$"
)


def parse_groups(
    exam_id: int,
    pages: list[Page],
) -> list[Group]:
    full_text = "\n".join(page.text for page in pages)

    matches = list(GROUP_PATTERN.finditer(full_text))

    if not matches:
        return [
            Group(
                exam_id=exam_id,
                name="SEM GRUPO",
                order=0,
                text=full_text.strip(),
            )
        ]

    groups: list[Group] = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)

        groups.append(
            Group(
                exam_id=exam_id,
                name=f"GRUPO {match.group(1)}",
                order=index,
                text=full_text[start:end].strip(),
            )
        )

    return groups