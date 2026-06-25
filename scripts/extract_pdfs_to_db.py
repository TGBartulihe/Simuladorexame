import re
import sqlite3
import time
from pathlib import Path

from pypdf import PdfReader

DB_PATH = Path("database/simuladorexame.db")
PDF_DIR = Path("storage/pdfs")

TARGETS = {
    "Port639": {"code": "639", "subject": "Português"},
    "MatA635": {"code": "635", "subject": "Matemática A"},
    "FQA715": {"code": "715", "subject": "Física e Química A"},
    "BG702": {"code": "702", "subject": "Biologia e Geologia"},
}


def identify_target(filename: str):
    lower = filename.lower()

    for pattern, meta in TARGETS.items():
        if pattern.lower() in lower:
            return meta

    return {
        "code": None,
        "subject": "Desconhecido",
    }


def classify_document(filename: str) -> str:
    name = filename.lower()

    if "-cc" in name or "_cc" in name:
        return "criteria"

    return "exam"


def extract_year(filename: str):
    match = re.search(r"(20\d{2})", filename)
    return int(match.group(1)) if match else None


def extract_phase(filename: str):
    match = re.search(r"[-_](F\d)[-_]", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    if re.search(r"[-_]EE[-_]", filename, re.IGNORECASE):
        return "EE"

    return None


def extract_version(filename: str):
    match = re.search(r"[-_]V(\d+)", filename, re.IGNORECASE)
    if match:
        return f"V{match.group(1)}"

    if "cad1" in filename.lower():
        return "Cad1"

    if "cad2" in filename.lower():
        return "Cad2"

    return "V1"


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, int, int]:
    reader = PdfReader(str(pdf_path))

    pages_text = []
    ok_pages = 0
    failed_pages = 0

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
            pages_text.append(f"\n\n--- PAGE {page_number} ---\n\n{text}")
            ok_pages += 1
        except Exception as e:
            pages_text.append(f"\n\n--- PAGE {page_number} ---\n\n[ERRO AO EXTRAIR PÁGINA: {e}]")
            failed_pages += 1

    return "\n".join(pages_text).strip(), ok_pages, failed_pages


def ensure_database_exists():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Base de dados não encontrada. Corre primeiro: python scripts\\init_database.py"
        )

    if not PDF_DIR.exists():
        raise FileNotFoundError("Pasta storage/pdfs não encontrada.")


def main():
    ensure_database_exists()

    pdfs = sorted(PDF_DIR.glob("*.pdf"))

    print(f"PDFs encontrados: {len(pdfs)}")

    processed = 0
    failed = 0
    total_failed_pages = 0

    started = time.time()

    with sqlite3.connect(DB_PATH) as conn:
        for pdf_path in pdfs:
            filename = pdf_path.name

            target = identify_target(filename)
            year = extract_year(filename)
            phase = extract_phase(filename)
            version = extract_version(filename)
            document_type = classify_document(filename)

            print(f"A processar: {filename}")

            try:
                extracted_text, ok_pages, failed_pages = extract_text_from_pdf(pdf_path)
                total_failed_pages += failed_pages

                conn.execute(
                    """
                    INSERT INTO documents (
                        filename,
                        url,
                        local_path,
                        year,
                        subject,
                        code,
                        phase,
                        version,
                        document_type,
                        extracted_text,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(filename) DO UPDATE SET
                        local_path = excluded.local_path,
                        year = excluded.year,
                        subject = excluded.subject,
                        code = excluded.code,
                        phase = excluded.phase,
                        version = excluded.version,
                        document_type = excluded.document_type,
                        extracted_text = excluded.extracted_text,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        filename,
                        None,
                        str(pdf_path),
                        year,
                        target["subject"],
                        target["code"],
                        phase,
                        version,
                        document_type,
                        extracted_text,
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO processing_log (
                        filename,
                        step,
                        status,
                        message
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        filename,
                        "extract_text",
                        "success" if failed_pages == 0 else "partial_success",
                        f"ok_pages={ok_pages}; failed_pages={failed_pages}; chars={len(extracted_text)}",
                    ),
                )

                processed += 1

            except Exception as e:
                failed += 1

                conn.execute(
                    """
                    INSERT INTO processing_log (
                        filename,
                        step,
                        status,
                        message
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        filename,
                        "extract_text",
                        "failed",
                        str(e),
                    ),
                )

                print(f"  ERRO: {e}")

        conn.commit()

    elapsed = round(time.time() - started, 2)

    print("")
    print("Extração concluída.")
    print(f"PDFs processados: {processed}")
    print(f"PDFs com falha total: {failed}")
    print(f"Páginas com falha parcial: {total_failed_pages}")
    print(f"Tempo: {elapsed}s")


if __name__ == "__main__":
    main()