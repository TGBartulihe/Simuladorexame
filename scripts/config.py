from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "library"
RAW = LIBRARY / "raw"
PARSED = LIBRARY / "parsed"
STORAGE = ROOT / "storage"
PDFS = STORAGE / "pdfs"
CRITERIA = STORAGE / "criteria"
ATTACHMENTS = STORAGE / "attachments"
INDEX_FILE = LIBRARY / "index.json"
SOURCE_URL = "https://iave.pt/provas-e-exames/provas-e-exames/provas-e-exames-finais-nacionais-es/"

for path in [LIBRARY, RAW, PARSED, STORAGE, PDFS, CRITERIA, ATTACHMENTS]:
    path.mkdir(parents=True, exist_ok=True)
