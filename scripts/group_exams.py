import re
import sqlite3
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")


def parse_document(filename: str):
    name = filename.replace(".pdf", "")

    patterns = {
        "Português": ("Port639", "639"),
        "Matemática A": ("MatA635", "635"),
        "Física e Química A": ("FQA715", "715"),
        "Biologia e Geologia": ("BG702", "702"),
    }

    subject = None
    code = None

    for subject_name, (pattern, subject_code) in patterns.items():
        if pattern.lower() in filename.lower():
            subject = subject_name
            code = subject_code
            break

    if not code:
        return None

    year_match = re.search(r"(20\d{2})", filename)
    year = int(year_match.group(1)) if year_match else None

    phase_match = re.search(r"[-_](F\d)[-_]", filename, re.IGNORECASE)
    if phase_match:
        phase = phase_match.group(1).upper()
    elif re.search(r"[-_]EE[-_]", filename, re.IGNORECASE):
        phase = "EE"
    else:
        phase = None

    version_match = re.search(r"[-_]V(\d+)", filename, re.IGNORECASE)
    if version_match:
        version = f"V{version_match.group(1)}"
    elif "cad1" in filename.lower():
        version = "Cad1"
    elif "cad2" in filename.lower():
        version = "Cad2"
    else:
        version = "V1"

    document_type = "criteria" if "-cc" in filename.lower() or "_cc" in filename.lower() else "exam"

    return {
        "subject": subject,
        "code": code,
        "year": year,
        "phase": phase,
        "version": version,
        "document_type": document_type,
    }


def main():
    with sqlite3.connect(DB_PATH) as conn:
        docs = conn.execute("""
            SELECT id, filename, document_type
            FROM documents
            WHERE code IN ('639', '635', '715', '702')
        """).fetchall()

        grouped = {}

        for doc_id, filename, stored_type in docs:
            parsed = parse_document(filename)

            if not parsed:
                continue

            # Critérios normalmente não têm versão real.
            # Agrupamos critérios por ano/código/fase.
            base_key = f"{parsed['year']}-{parsed['code']}-{parsed['phase']}"

            if base_key not in grouped:
                grouped[base_key] = {
                    "exam_key": base_key,
                    "year": parsed["year"],
                    "subject": parsed["subject"],
                    "code": parsed["code"],
                    "phase": parsed["phase"],
                    "version": None,
                    "exam_document_ids": [],
                    "criteria_document_ids": [],
                }

            if parsed["document_type"] == "criteria":
                grouped[base_key]["criteria_document_ids"].append(doc_id)
            else:
                grouped[base_key]["exam_document_ids"].append(doc_id)

        inserted = 0

        for key, data in grouped.items():
            exam_document_id = data["exam_document_ids"][0] if data["exam_document_ids"] else None
            criteria_document_id = data["criteria_document_ids"][0] if data["criteria_document_ids"] else None

            conn.execute("""
                INSERT INTO exams (
                    exam_key,
                    year,
                    subject,
                    code,
                    phase,
                    version,
                    exam_document_id,
                    criteria_document_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_key) DO UPDATE SET
                    exam_document_id = excluded.exam_document_id,
                    criteria_document_id = excluded.criteria_document_id
            """, (
                key,
                data["year"],
                data["subject"],
                data["code"],
                data["phase"],
                data["version"],
                exam_document_id,
                criteria_document_id,
            ))

            inserted += 1

        conn.commit()

    print(f"Exames agrupados/atualizados: {inserted}")


if __name__ == "__main__":
    main()