from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Group:
    exam_id: int
    name: str
    order: int
    text: str