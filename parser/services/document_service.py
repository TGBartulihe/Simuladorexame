from __future__ import annotations

import hashlib
from pathlib import Path

from parser.database.repository import Repository


class DocumentService:

    def __init__(self):

        self.repository = Repository()

    # ==========================================================
    # HASH
    # ==========================================================

    @staticmethod
    def sha256(path: Path) -> str:

        h = hashlib.sha256()

        with path.open("rb") as f:

            while True:

                chunk = f.read(1024 * 1024)

                if not chunk:
                    break

                h.update(chunk)

        return h.hexdigest()

    # ==========================================================
    # DOCUMENT EXISTS
    # ==========================================================

    def exists(self, filename: str):

        return self.repository.get_document_by_filename(
            filename
        )

    # ==========================================================
    # REGISTER
    # ==========================================================

    def register_pdf(

        self,

        pdf_path: Path,

        document_type: str,

        extracted_text: str,

        subject: str | None = None,

        year: int | None = None,

        phase: str | None = None,

        code: str | None = None,

    ) -> int:

        filename = pdf_path.name

        existing = self.exists(filename)

        if existing:

            return existing["id"]

        return self.repository.insert_document(

            filename=filename,

            document_type=document_type,

            extracted_text=extracted_text,

            sha256=self.sha256(pdf_path),

            subject=subject,

            year=year,

            phase=phase,

            code=code,

        )

    # ==========================================================

    def get(self, document_id: int):

        return self.repository.get_document(document_id)

    # ==========================================================

    def close(self):

        self.repository.close()