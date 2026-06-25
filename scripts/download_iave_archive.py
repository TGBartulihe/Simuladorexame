import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START_URLS = [
    "https://iave.pt/provas-e-exames/provas-e-exames/provas-e-exames-finais-nacionais-es/",
    "https://iave.pt/provas-e-exames/arquivo/arquivo-provas-e-exames-finais-nacionais-es/",
]

DOMAIN = "https://iave.pt"
OUT_DIR = Path("storage/pdfs")
LIBRARY_DIR = Path("library")
MANIFEST_PATH = LIBRARY_DIR / "iave_archive_manifest.json"

ALLOWED_EXTENSIONS = (".pdf", ".zip", ".mp3", ".wav")
CRAWL_LIMIT = 5000
REQUEST_DELAY = 0.4

HEADERS = {
    "User-Agent": "Mozilla/5.0 (educational proof of concept; private local archive)"
}

OUT_DIR.mkdir(parents=True, exist_ok=True)
LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def is_iave_url(url: str) -> bool:
    return url.startswith(DOMAIN)


def clean_url(url: str) -> str:
    return url.split("#")[0].strip()


def safe_filename(url: str) -> str:
    path = urlparse(url).path
    name = Path(path).name
    name = re.sub(r"[^\w.\-()]+", "_", name)
    return name or "file"


def classify_file(url: str, label: str) -> str:
    text = f"{url} {label}".lower()

    if "-cc" in text or "_cc" in text or "criter" in text or "classifica" in text:
        return "criteria"

    if "audio" in text or text.endswith(".mp3") or text.endswith(".wav"):
        return "audio"

    if text.endswith(".zip"):
        return "archive"

    if "adapt" in text or "adp" in text:
        return "adapted_exam"

    if "ex-" in text or "prova" in text or "exame" in text:
        return "exam"

    return "other"


def extract_year(url: str, label: str):
    text = f"{url} {label}"
    match = re.search(r"(19\d{2}|20\d{2})", text)
    return int(match.group(1)) if match else None


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def download_file(url: str, path: Path):
    with requests.get(url, headers=HEADERS, timeout=90, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)


def main():
    to_visit = [clean_url(u) for u in START_URLS]
    visited = set()
    assets = {}

    while to_visit and len(visited) < CRAWL_LIMIT:
        url = to_visit.pop(0)

        if url in visited:
            continue

        if not is_iave_url(url):
            continue

        visited.add(url)
        print(f"[crawl] {len(visited)} {url}")

        try:
            html = fetch_html(url)
        except Exception as e:
            print(f"  erro ao abrir página: {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = clean_url(urljoin(url, a["href"]))
            label = a.get_text(" ", strip=True)

            lower = href.lower()

            if any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                filename = safe_filename(href)
                assets[href] = {
                    "url": href,
                    "label": label,
                    "filename": filename,
                    "file_type": classify_file(href, label),
                    "year": extract_year(href, label),
                    "source_page": url,
                    "local_path": str(OUT_DIR / filename),
                    "download_status": "pending",
                }
                continue

            if is_iave_url(href):
                relevant = any(token in lower for token in [
                    "provas-e-exames",
                    "arquivo",
                    "wp-content/uploads",
                    "exames-finais-nacionais",
                    "ensino-secundario",
                ])

                if relevant and href not in visited and href not in to_visit:
                    to_visit.append(href)

        time.sleep(REQUEST_DELAY)

    print("")
    print(f"Páginas visitadas: {len(visited)}")
    print(f"Ficheiros encontrados: {len(assets)}")
    print("")

    downloaded = 0
    skipped = 0
    failed = 0

    for item in assets.values():
        path = Path(item["local_path"])

        if path.exists() and path.stat().st_size > 0:
            item["download_status"] = "exists"
            skipped += 1
            continue

        print(f"[download] {item['filename']}")

        try:
            download_file(item["url"], path)
            item["download_status"] = "downloaded"
            downloaded += 1
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            item["download_status"] = "error"
            item["error"] = str(e)
            failed += 1
            print(f"  erro: {e}")

    manifest = {
        "source": "IAVE",
        "start_urls": START_URLS,
        "visited_pages": sorted(visited),
        "total_pages_visited": len(visited),
        "total_assets_found": len(assets),
        "downloaded": downloaded,
        "skipped_existing": skipped,
        "failed": failed,
        "assets": sorted(assets.values(), key=lambda x: (x["year"] or 0, x["filename"])),
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("")
    print("Concluído.")
    print(f"Novos downloads: {downloaded}")
    print(f"Já existiam: {skipped}")
    print(f"Falhas: {failed}")
    print(f"Manifesto: {MANIFEST_PATH}")
    print(f"Pasta: {OUT_DIR}")


if __name__ == "__main__":
    main()