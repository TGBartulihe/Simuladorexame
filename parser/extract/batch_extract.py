from __future__ import annotations

from pathlib import Path

from rich.progress import track

from parser.extract.extract_pdf import PDFExtractor
from parser.services.document_service import DocumentService


class BatchExtractor:

    def __init__(self):

        self.extractor = PDFExtractor()

        self.documents = DocumentService()

        # CORREÇÃO: acumula os avisos de corrupção de glifo (ver
        # extract_pdf.py) detectados durante o lote, para imprimir um
        # resumo ao final. Antes, esse problema (texto tipo
        # "/g14/g14/g16/g32" em vez do caractere real) passava
        # completamente silencioso — só foi descoberto numa auditoria
        # manual do banco de dados, muito depois da extração.
        self.flagged_documents: list[tuple[str, list]] = []

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

            if self.extractor.warnings:
                self.flagged_documents.append((pdf.name, list(self.extractor.warnings)))

            self.documents.register_pdf(

                pdf_path=pdf,

                document_type=document_type,

                extracted_text=text,

            )

        self.documents.close()

        self._report_flagged_documents()

    def _report_flagged_documents(self) -> None:
        if not self.flagged_documents:
            return

        print()
        print("=" * 60)
        print(f"ATENÇÃO: {len(self.flagged_documents)} documento(s) com possível")
        print("corrupção de fonte simbólica — revisar manualmente:")
        print("=" * 60)
        for filename, warnings in self.flagged_documents:
            print(f"  {filename}")
            for w in warnings:
                print(f"    - {w.detail}")
        print("=" * 60)
