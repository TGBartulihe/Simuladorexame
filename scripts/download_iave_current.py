import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://iave.pt/provas-e-exames/provas-e-exames/provas-e-exames-finais-nacionais-es/"
OUT_DIR = "storage/pdfs"
INDEX_FILE = "library/iave_download_index.json"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs("library", exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 - educational proof of concept"
}

def safe_name(url):
    path = urlparse(url).path
    name = os.path.basename(path)
    return name or "file.pdf"

def main():
    print("A consultar página do IAVE...")
    r = requests.get(BASE_URL, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    files = []
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, a["href"])
        label = a.get_text(" ", strip=True)

        if any(ext in href.lower() for ext in [".pdf", ".mp3", ".zip"]):
            files.append({
                "label": label,
                "url": href,
                "filename": safe_name(href)
            })

    print(f"Ficheiros encontrados: {len(files)}")

    downloaded = []

    for item in files:
        url = item["url"]
        filename = item["filename"]
        path = os.path.join(OUT_DIR, filename)

        if os.path.exists(path):
            print(f"Já existe: {filename}")
            item["local_path"] = path
            item["status"] = "exists"
            downloaded.append(item)
            continue

        print(f"A baixar: {filename}")
        try:
            res = requests.get(url, headers=headers, timeout=60)
            res.raise_for_status()

            with open(path, "wb") as f:
                f.write(res.content)

            item["local_path"] = path
            item["status"] = "downloaded"
            downloaded.append(item)

            time.sleep(0.7)

        except Exception as e:
            item["status"] = "error"
            item["error"] = str(e)
            downloaded.append(item)
            print(f"Erro: {filename} -> {e}")

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(downloaded, f, ensure_ascii=False, indent=2)

    print("")
    print("Concluído.")
    print(f"Índice criado em: {INDEX_FILE}")
    print(f"Ficheiros guardados em: {OUT_DIR}")

if __name__ == "__main__":
    main()