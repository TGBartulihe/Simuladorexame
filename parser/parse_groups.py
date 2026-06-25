from __future__ import annotations

import re

from parser.models import Group, Page


# Apenas grupos realmente utilizados nos exames nacionais.
GROUP_PATTERN = re.compile(
    r"(?im)^\s*GRUPO\s+(I|II|III|IV|V)\s*$"
)


def parse_groups(
    exam_id: int,
    pages: list[Page],
) -> list[Group]:

    groups: list[Group] = []

    current_group = None
    current_lines: list[str] = []

    order = 0

    def flush():

        nonlocal order
        nonlocal current_group
        nonlocal current_lines

        if current_group is None:
            return

        groups.append(
            Group(
                exam_id=exam_id,
                name=current_group,
                order=order,
                text="\n".join(current_lines).strip(),
            )
        )

        order += 1
        current_lines = []

    for page in pages:

        for line in page.text.splitlines():

            match = GROUP_PATTERN.match(line)

            if match:

                flush()

                current_group = f"GRUPO {match.group(1)}"

                continue

            if current_group is not None:

                current_lines.append(line)

    flush()

    return groups