from __future__ import annotations

from pathlib import Path

from rich.progress import track

from parser.extract.extract_pdf import PDFExtractor
from parser.services.document_service import DocumentService


class BatchExtractor:

    def __init__(self):

        self.extractor = PDFExtractor()

        self.documents = DocumentService()

    def run(

        self,

        folder: Path,

        document_type: str,

    ):

        pdfs = sorted(folder.glob("*.pdf"))

        for pdf in track(

            pdfs,

            description="Extraindo PDFs",

        ):

            text = self.extractor.extract(pdf)

            self.documents.register_pdf(

                pdf_path=pdf,

                document_type=document_type,

                extracted_text=text,

            )

        self.documents.close()