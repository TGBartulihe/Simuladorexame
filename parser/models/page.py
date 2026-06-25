from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Page:
    number: int
    text: str