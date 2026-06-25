import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ARCHIVE_URL = "https://iave.pt/provas-e-exames/arquivo/arquivo-provas-e-exames-finais-nacionais-es/?ano={year}"

MIN_YEAR = 2012
MAX_YEAR = 2026

TARGETS = {
    "Port639": {"code": "639", "subject": "Português"},
    "MatA635": {"code": "635", "subject": "Matemática A"},
    "FQA715": {"code": "715", "subject": "Física e Química A"},
    "BG702": {"code": "702", "subject": "Biologia e Geologia"},
}

OUT_DIR = Path("storage/pdfs")
MANIFEST = Path("library/iave_mikaela_manifest.json")

OUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 educational proof of concept"
}


def clean_url(url: str) -> str:
    return url.split("#")[0].strip()


def safe_filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    return re.sub(r"[^\w.\-()]+", "_", name)


def identify_target(filename: str):
    name = filename.lower()

    for pattern, meta in TARGETS.items():
        if pattern.lower() in name:
            return meta

    return None


def is_allowed_pdf(filename: str) -> bool:
    name = filename.lower()

    if not name.endswith(".pdf"):
        return False

    if identify_target(filename) is None:
        return False

    if "adp" in name or "adapt" in name:
        return False

    if name.startswith("ex-"):
        return True

    return False


def classify_document(filename: str) -> str:
    name = filename.lower()

    if "-cc" in name or "_cc" in name:
        return "criteria"

    return "exam"


def extract_phase(filename: str):
    match = re.search(r"-F(\d)-", filename, re.IGNORECASE)
    if match:
        return f"F{match.group(1)}"

    if "-ee-" in filename.lower():
        return "EE"

    return None


def extract_version(filename: str):
    match = re.search(r"-V(\d)", filename, re.IGNORECASE)
    if match:
        return f"V{match.group(1)}"

    return "V1"


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def download_file(url: str, path: Path):
    with requests.get(url, headers=HEADERS, timeout=90, stream=True) as response:
        response.raise_for_status()

        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)


def collect_assets_for_year(year: int):
    page_url = ARCHIVE_URL.format(year=year)
    print(f"[year] {year}")

    html = fetch_html(page_url)
    soup = BeautifulSoup(html, "html.parser")

    assets = []

    for link in soup.find_all("a", href=True):
        href = clean_url(urljoin(page_url, link["href"]))

        if not href.startswith("https://iave.pt"):
            continue

        filename = safe_filename(href)

        if not is_allowed_pdf(filename):
            continue

        target = identify_target(filename)

        assets.append({
            "year": year,
            "code": target["code"],
            "subject": target["subject"],
            "document_type": classify_document(filename),
            "phase": extract_phase(filename),
            "version": extract_version(filename),
            "filename": filename,
            "url": href,
            "local_path": str(OUT_DIR / filename),
            "source_page": page_url,
            "status": "pending",
        })

    return assets


def main():
    all_assets = {}

    for year in range(MAX_YEAR, MIN_YEAR - 1, -1):
        try:
            assets = collect_assets_for_year(year)

            for asset in assets:
                all_assets[asset["url"]] = asset

            print(f"  encontrados: {len(assets)}")

        except Exception as e:
            print(f"  erro no ano {year}: {e}")

        time.sleep(0.25)

    print("")
    print(f"Total filtrado: {len(all_assets)}")
    print("")

    downloaded = 0
    skipped = 0
    failed = 0

    for asset in all_assets.values():
        path = Path(asset["local_path"])

        if path.exists() and path.stat().st_size > 0:
            asset["status"] = "exists"
            skipped += 1
            continue

        print(
            f"[download] {asset['year']} | {asset['subject']} | "
            f"{asset['phase']} | {asset['document_type']} | {asset['filename']}"
        )

        try:
            download_file(asset["url"], path)
            asset["status"] = "downloaded"
            downloaded += 1
            time.sleep(0.25)

        except Exception as e:
            asset["status"] = "error"
            asset["error"] = str(e)
            failed += 1
            print(f"  erro: {e}")

    manifest = {
        "student_case": "Mikaela",
        "target_subjects": TARGETS,
        "min_year": MIN_YEAR,
        "max_year": MAX_YEAR,
        "total_assets": len(all_assets),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "assets": list(all_assets.values()),
    }

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("")
    print("Concluído.")
    print(f"Ficheiros encontrados: {len(all_assets)}")
    print(f"Baixados: {downloaded}")
    print(f"Já existiam: {skipped}")
    print(f"Falhas: {failed}")
    print(f"Manifesto: {MANIFEST}")


if __name__ == "__main__":
    main()