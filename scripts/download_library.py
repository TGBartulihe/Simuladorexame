"""Download PDFs referenced by library/index.json into storage/.

PDFs are ignored by Git. This script is incremental: existing files are skipped.
"""
import json
import re
import requests
from pathlib import Path
from config import INDEX_FILE, PDFS, CRITERIA, ATTACHMENTS


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    return value.strip("-") or "asset.pdf"


def download(url: str, target: Path) -> bool:
    if not url:
        return False
    if target.exists() and target.stat().st_size > 0:
        print(f"skip existing: {target}")
        return True
    print(f"download: {url}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    target.write_bytes(response.content)
    return True


def main():
    if not INDEX_FILE.exists():
        raise SystemExit("library/index.json not found. Run discover_library.py first.")

    manifest = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    for item in manifest.get("items", []):
        exam_id = item["examId"]
        files = item.get("files", {})
        download(files.get("examPdfUrl", ""), PDFS / f"{safe_name(exam_id)}.pdf")
        download(files.get("criteriaPdfUrl", ""), CRITERIA / f"{safe_name(exam_id)}-criteria.pdf")
        for idx, url in enumerate(files.get("attachments", []), start=1):
            download(url, ATTACHMENTS / f"{safe_name(exam_id)}-attachment-{idx}.pdf")


if __name__ == "__main__":
    main()
