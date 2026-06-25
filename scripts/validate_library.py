import json
from config import INDEX_FILE, PARSED


def main():
    errors = []
    if not INDEX_FILE.exists():
        errors.append("Missing library/index.json")
    parsed_index = PARSED / "index.json"
    if not parsed_index.exists():
        errors.append("Missing library/parsed/index.json")
    else:
        items = json.loads(parsed_index.read_text(encoding="utf-8"))
        for item in items:
            if not (PARSED / f"{item['examId']}.json").exists():
                errors.append(f"Missing parsed exam: {item['examId']}")
    if errors:
        print("Validation failed:")
        for err in errors:
            print(f"- {err}")
        raise SystemExit(1)
    print("Validation OK")


if __name__ == "__main__":
    main()
