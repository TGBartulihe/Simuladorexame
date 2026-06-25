from __future__ import annotations

from pathlib import Path
import re
import fitz
import pdfplumber

from parser.logger import get_logger

log = get_logger(__name__)


# CORREÇÃO — bug encontrado na auditoria do banco: pelo menos 1 trecho de
# texto extraído (envolvendo fórmulas/expressões em fonte simbólica, comum
# em provas de Matemática/Física) veio com glifos sem mapeamento Unicode,
# tipo "/g14/g14/g16/g32" em vez do caractere real. _looks_valid() (mais
# abaixo) não detectava isto porque só audita o tamanho total do texto e
# a presença de 3 palavras-chave genéricas ("GRUPO", "Página", "Prova") —
# um documento de 50 páginas pode ter esses requisitos satisfeitos mesmo
# com 1 página de fórmulas ilegível.
#
# Esta correção NÃO recupera o texto perdido (a informação já não existe
# depois que o glifo virou um código CID sem ToUnicode map — isso é uma
# limitação do PDF de origem, não da biblioteca de extração). O que ela
# faz é DETECTAR e reportar, em vez de deixar passar silenciosamente, para
# que o documento possa ser marcado para revisão manual ou reprocessado
# com outra estratégia (ex: OCR sobre o render da página, que lê o glifo
# visualmente em vez de depender do mapeamento interno da fonte).
GLYPH_CORRUPTION_PATTERN = re.compile(r"(?:/g\d+){2,}")


class PDFExtractionWarning:
    """Sinaliza um problema de qualidade detectado na extração, sem
    impedir que o texto extraído seja usado — a decisão de descartar ou
    marcar para revisão fica com quem chama PDFExtractor.extract().
    """

    def __init__(self, kind: str, detail: str):
        self.kind = kind
        self.detail = detail

    def __repr__(self) -> str:
        return f"PDFExtractionWarning(kind={self.kind!r}, detail={self.detail!r})"


class PDFExtractor:

    def __init__(self):

        self.method = None
        self.warnings: list[PDFExtractionWarning] = []

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def extract(self, pdf: Path) -> str:

        if not pdf.exists():
            raise FileNotFoundError(pdf)

        self.warnings = []

        try:

            text = self._extract_pymupdf(pdf)

            self.method = "PyMuPDF"

            if self._looks_valid(text):

                self._check_glyph_corruption(pdf, text)
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

        self._check_glyph_corruption(pdf, text)
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

    def _check_glyph_corruption(self, pdf: Path, text: str) -> None:
        """Verifica corrupção de fonte simbólica por PÁGINA (não no texto
        inteiro), para conseguir reportar em qual página está o problema
        — isso é informação útil tanto para revisão manual quanto para um
        eventual reprocessamento via OCR de só essa página, em vez do
        documento inteiro.
        """
        pages = text.split("--- PAGE ")

        for page_block in pages:
            if not page_block.strip():
                continue

            matches = GLYPH_CORRUPTION_PATTERN.findall(page_block)
            if matches:
                page_label = page_block.split("---", 1)[0].strip()
                self.warnings.append(
                    PDFExtractionWarning(
                        kind="glyph_corruption",
                        detail=f"página {page_label}: {len(matches)} sequência(s) de glifo sem mapeamento (ex: {matches[0]})",
                    )
                )
                log.warning(
                    "%s: possível corrupção de fonte simbólica na página %s (%d ocorrência(s))",
                    pdf.name,
                    page_label,
                    len(matches),
                )
