from __future__ import annotations

from pathlib import Path
import fitz
import pdfplumber

from parser.logger import get_logger

log = get_logger(__name__)


class PDFExtractor:

    def __init__(self):

        self.method = None

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def extract(self, pdf: Path) -> str:

        if not pdf.exists():
            raise FileNotFoundError(pdf)

        try:

            text = self._extract_pymupdf(pdf)

            self.method = "PyMuPDF"

            if self._looks_valid(text):

                return text

            log.warning(
                "%s extraído com pouco texto usando PyMuPDF. "
                "Tentando pdfplumber.",
                pdf.name,
            )

        except Exception as ex:

            log.warning(
                "PyMuPDF falhou em %s: %s",
                pdf.name,
                ex,
            )

        text = self._extract_pdfplumber(pdf)

        self.method = "pdfplumber"

        return text

    # ==========================================================
    # PYMUPDF
    # ==========================================================

    def _extract_pymupdf(self, pdf: Path) -> str:

        pages = []

        document = fitz.open(pdf)

        try:

            for page_number, page in enumerate(document, start=1):

                pages.append(
                    f"--- PAGE {page_number} ---\n"
                )

                pages.append(
                    page.get_text("text")
                )

        finally:

            document.close()

        return "\n".join(pages)

    # ==========================================================
    # PDFPLUMBER
    # ==========================================================

    def _extract_pdfplumber(self, pdf: Path) -> str:

        pages = []

        with pdfplumber.open(pdf) as document:

            for page_number, page in enumerate(document.pages, start=1):

                pages.append(
                    f"--- PAGE {page_number} ---\n"
                )

                txt = page.extract_text()

                if txt:

                    pages.append(txt)

        return "\n".join(pages)

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @staticmethod
    def _looks_valid(text: str) -> bool:

        if len(text) < 3000:

            return False

        required = [

            "GRUPO",

            "Página",

            "Prova",

        ]

        found = 0

        upper = text.upper()

        for word in required:

            if word.upper() in upper:

                found += 1

        return found >= 2