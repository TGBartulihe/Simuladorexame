import sqlite3
import json
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")

with sqlite3.connect(DB_PATH) as conn:
    rows = conn.execute("""
        SELECT
            e.exam_key,
            e.subject,
            c.status,
            c.model,
            LENGTH(c.structured_json),
            c.structured_json,
            c.error_message
        FROM ai_exam_cache c
        JOIN exams e ON e.id = c.exam_id
        ORDER BY c.updated_at DESC
        LIMIT 5
    """).fetchall()

for row in rows:
    exam_key, subject, status, model, length, structured_json, error = row

    print("=" * 80)
    print(exam_key, subject)
    print("status:", status)
    print("model:", model)
    print("json length:", length)
    print("error:", error)

    if structured_json:
        data = json.loads(structured_json)
        print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])