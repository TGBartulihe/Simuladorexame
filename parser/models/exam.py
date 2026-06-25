from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Exam:
    id: int
    exam_key: str
    year: int
    subject: str
    code: str
    phase: str
    exam_document_id: int
    criteria_document_id: int | None