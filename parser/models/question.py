from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Question:
    exam_id: int
    group: str
    number: str
    statement: str
    criteria: str | None = None
    choices: list[dict] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)