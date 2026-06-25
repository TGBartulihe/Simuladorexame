import sqlite3
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

schema = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    url TEXT,
    local_path TEXT NOT NULL,
    year INTEGER,
    subject TEXT,
    code TEXT,
    phase TEXT,
    version TEXT,
    document_type TEXT,
    extracted_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_key TEXT UNIQUE,
    year INTEGER,
    subject TEXT,
    code TEXT,
    phase TEXT,
    version TEXT,
    exam_document_id INTEGER,
    criteria_document_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_document_id) REFERENCES documents(id),
    FOREIGN KEY (criteria_document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS ai_exam_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    model TEXT,
    prompt_version TEXT,
    input_hash TEXT,
    structured_json TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(id)
);

CREATE TABLE IF NOT EXISTS processing_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    step TEXT,
    status TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

with sqlite3.connect(DB_PATH) as conn:
    conn.executescript(schema)

print(f"Database pronta em: {DB_PATH}")

