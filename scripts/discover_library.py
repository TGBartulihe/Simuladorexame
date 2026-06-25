"""Discover IAVE exam assets and build library/index.json.

Initial version: creates a manifest structure with a seed example.
Next step: replace SEED_ITEMS with real discovery from IAVE HTML pages.
"""
import json
from datetime import datetime, timezone
from config import INDEX_FILE, SOURCE_URL

SEED_ITEMS = [
    {
        "examId": "seed-2025-portugues-639-f1-v1",
        "source": "IAVE",
        "sourcePage": SOURCE_URL,
        "year": 2025,
        "subject": "Português",
        "code": "639",
        "phase": "1",
        "version": "1",
        "files": {
            "examPdfUrl": "",
            "criteriaPdfUrl": "",
            "attachments": []
        },
        "status": "pending_urls"
    }
]


def main():
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_URL,
        "items": SEED_ITEMS,
    }
    INDEX_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {INDEX_FILE} with {len(SEED_ITEMS)} seed item(s).")


if __name__ == "__main__":
    main()
