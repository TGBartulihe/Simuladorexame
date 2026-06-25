from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class Document:

    id: int
    filename: str
    document_type: str
    extracted_text: str


@dataclass(slots=True)
class Exam:

    id: int
    exam_key: str
    year: int
    subject: str
    code: str
    phase: str
    exam_document_id: int
    criteria_document_id: int


@dataclass(slots=True)
class Page:

    number: int
    text: str


@dataclass(slots=True)
class Group:

    exam_id: int
    name: str
    order: int
    text: str


@dataclass(slots=True)
class Question:

    exam_id: int

    group: str

    number: str

    statement: str

    criteria: Optional[str] = None

    choices: list[str] = field(default_factory=list)

    images: list[str] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)