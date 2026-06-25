from __future__ import annotations

import re
from dataclasses import dataclass

from parser.models import Group
from parser.utils.question_boundaries import find_question_starts


@dataclass(slots=True)
class ParsedContext:
    key: str
    title: str | None
    raw_text: str


CONTEXT_TITLE = re.compile(
    r"(?im)^\s*(Texto\s+\d+|Figura\s+\d+|Gráfico\s+\d+|Tabela\s+\d+|Documento\s+\d+)\s*$"
)


def extract_group_context(group: Group) -> ParsedContext | None:
    # CORREÇÃO: antes usava um regex local (QUESTION_START) quase
    # idêntico, mas não exatamente igual, ao usado em parse_questions.py.
    # Agora os dois módulos usam a mesma função (find_question_starts),
    # então não há mais risco de discordarem sobre onde a primeira
    # questão real começa — o que também corrige, aqui, o mesmo bug de
    # tabela de cotações sendo tratada como divisor de contexto/questão.
    matches = find_question_starts(group.text)

    if not matches:
        raw = group.text.strip()
    else:
        raw = group.text[: matches[0].start()].strip()

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
