from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Document:
    id: int
    filename: str
    document_type: str
    extracted_text: str