from __future__ import annotations

import re
from dataclasses import dataclass

from parser.models import Group


@dataclass(slots=True)
class ParsedContext:
    key: str
    title: str | None
    raw_text: str


QUESTION_START = re.compile(
    r"(?m)^\s*(?:[1-9][0-9]?)(?:\.[1-9][0-9]?)?\.\s+"
)

CONTEXT_TITLE = re.compile(
    r"(?im)^\s*(Texto\s+\d+|Figura\s+\d+|Gráfico\s+\d+|Tabela\s+\d+|Documento\s+\d+)\s*$"
)


def extract_group_context(group: Group) -> ParsedContext | None:
    match = QUESTION_START.search(group.text)

    if not match:
        raw = group.text.strip()
    else:
        raw = group.text[: match.start()].strip()

    if len(raw) < 120:
        return None

    title = _find_title(raw)

    return ParsedContext(
        key=f"{group.name}-context",
        title=title,
        raw_text=raw,
    )


def extract_contexts(groups: list[Group]) -> dict[str, ParsedContext]:
    contexts: dict[str, ParsedContext] = {}

    for group in groups:
        context = extract_group_context(group)

        if context:
            contexts[group.name] = context

    return contexts


def _find_title(raw: str) -> str | None:
    for line in raw.splitlines():
        line = line.strip()

        if CONTEXT_TITLE.match(line):
            return line

    return None