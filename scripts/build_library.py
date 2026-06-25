"""Build normalized JSON exams from extracted text.

This first version creates placeholder parsed records so the UI can work.
Real parsing rules will be added per exam family/discipline.
"""
import json
from datetime import datetime, timezone
from config import INDEX_FILE, RAW, PARSED


def main():
    if not INDEX_FILE.exists():
        raise SystemExit("library/index.json not found. Run discover_library.py first.")

    manifest = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    parsed_index = []

    for item in manifest.get("items", []):
        exam_id = item["examId"]
        exam_text_files = list(RAW.glob(f"{exam_id}*.exam.txt"))
        criteria_text_files = list(RAW.glob(f"{exam_id}*.criteria.txt"))
        exam_text = exam_text_files[0].read_text(encoding="utf-8") if exam_text_files else ""
        criteria_text = criteria_text_files[0].read_text(encoding="utf-8") if criteria_text_files else ""

        parsed = {
            "examId": exam_id,
            "title": f"{item.get('subject')} {item.get('code')} - {item.get('year')} - Fase {item.get('phase')}",
            "metadata": item,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "questions": [
                {
                    "id": f"{exam_id}-q1",
                    "number": "1",
                    "type": "open_text",
                    "statement": exam_text[:1500] if exam_text else "Pergunta pendente de extração.",
                    "maxScore": None,
                    "officialCriteria": criteria_text[:1500] if criteria_text else "Critério pendente de extração.",
                    "correctionMode": "rubric"
                }
            ]
        }
        out = PARSED / f"{exam_id}.json"
        out.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        parsed_index.append({"examId": exam_id, "file": f"library/parsed/{exam_id}.json", "title": parsed["title"]})

    (PARSED / "index.json").write_text(json.dumps(parsed_index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built {len(parsed_index)} parsed exam record(s).")


if __name__ == "__main__":
    main()
