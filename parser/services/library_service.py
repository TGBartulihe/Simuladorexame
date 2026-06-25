from __future__ import annotations

from pathlib import Path

from rich.progress import track

from parser.extract.extract_pdf import PDFExtractor
from parser.extract.classify_document import DocumentClassifier
from parser.services.document_service import DocumentService


class LibraryService:

    def __init__(self):

        self.extractor = PDFExtractor()

        self.classifier = DocumentClassifier()

        self.documents = DocumentService()

    def import_folder(

        self,

        folder: Path,

    ):

        pdfs = sorted(folder.glob("*.pdf"))

        for pdf in track(

            pdfs,

            description="Biblioteca",

        ):

            text = self.extractor.extract(pdf)

            meta = self.classifier.classify(

                pdf.name,

                text,

            )

            self.documents.register_pdf(

                pdf_path=pdf,

                document_type=meta.document_type,

                extracted_text=text,

                subject=meta.subject,

                year=meta.year,

                phase=meta.phase,

                code=meta.code,

            )

        self.documents.close()