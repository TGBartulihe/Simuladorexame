from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class QuestionContext:
    id: int | None
    exam_id: int
    group_id: int | None
    context_key: str
    title: str | None
    raw_text: str