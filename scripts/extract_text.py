"""Extract text from downloaded PDFs into library/raw/*.txt."""
from pypdf import PdfReader
from config import PDFS, CRITERIA, RAW


def extract_pdf(path):
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"\n\n--- PAGE {i} ---\n{text}")
    return "".join(pages).strip()


def main():
    count = 0
    for folder, suffix in [(PDFS, "exam"), (CRITERIA, "criteria")]:
        for pdf in folder.glob("*.pdf"):
            out = RAW / f"{pdf.stem}.{suffix}.txt"
            if out.exists() and out.stat().st_size > 0:
                print(f"skip existing: {out}")
                continue
            print(f"extract: {pdf}")
            out.write_text(extract_pdf(pdf), encoding="utf-8")
            count += 1
    print(f"Extracted {count} file(s).")


if __name__ == "__main__":
    main()
