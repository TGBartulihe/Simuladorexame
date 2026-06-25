import re
import sqlite3
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")


def ensure_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS question_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            group_name TEXT,
            question_number TEXT,
            raw_statement TEXT,
            raw_criteria TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exam_id) REFERENCES exams(id)
        );
    """)

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_question_blocks_unique
        ON question_blocks (exam_id, group_name, question_number);
    """)


def clean_text(text):
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_groups(text):
    pattern = re.compile(
        r"(GRUPO\s+[IVXLCDM]+|Grupo\s+[IVXLCDM]+)",
        re.IGNORECASE
    )

    matches = list(pattern.finditer(text))

    if not matches:
        return [("Sem grupo", text)]

    groups = []

    for i, match in enumerate(matches):
        group_name = match.group(1).strip().upper()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        group_text = text[start:end].strip()
        groups.append((group_name, group_text))

    return groups


def looks_like_real_question(block):
    starters = [
        "selecione",
        "identifique",
        "explique",
        "complete",
        "associe",
        "ordene",
        "transcreva",
        "indique",
        "apresente",
        "justifique",
        "calcule",
        "determine",
        "mostre",
        "considere",
    ]

    lower = block.lower()

    if any(word in lower[:400] for word in starters):
        return True

    if "(a)" in lower[:700] and "(b)" in lower[:900]:
        return True

    if "escreva" in lower[:500] and "folha de respostas" in lower[:800]:
        return True

    return False


def split_questions(group_text):
    # Aceita:
    # 1.
    # 2.
    # 15.
    # 15.1.
    # 15.2.
    #
    # Rejeita:
    # 0
    # números soltos de gráficos/tabelas
    pattern = re.compile(
        r"(?m)^\s*((?:[1-9]\d?)(?:\.[1-9]\d?)?)\.\s+"
    )

    matches = list(pattern.finditer(group_text))

    if not matches:
        return []

    questions = []

    for i, match in enumerate(matches):
        qnum = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(group_text)
        qtext = group_text[start:end].strip()

        if len(qtext) < 120:
            continue

        if not looks_like_real_question(qtext):
            continue

        questions.append((qnum, qtext))

    return questions


def find_criteria_for_question(criteria_text, group_name, question_number):
    if not criteria_text:
        return None

    q = re.escape(question_number)

    patterns = [
        rf"(?is)(?:Item|Questão|Q\.?)\s*{q}\b(.{{0,2500}})",
        rf"(?is)^\s*{q}\s+(.{{0,2500}})",
        rf"(?is)\n\s*{q}\s+(.{{0,2500}})",
    ]

    for pattern in patterns:
        match = re.search(pattern, criteria_text)
        if match:
            return match.group(0).strip()

    if group_name:
        group_pattern = re.escape(group_name)
        match = re.search(rf"(?is){group_pattern}(.{{0,3000}})", criteria_text)
        if match:
            return match.group(0).strip()

    return None


def main():
    with sqlite3.connect(DB_PATH) as conn:
        ensure_tables(conn)

        conn.execute("DELETE FROM question_blocks")
        conn.commit()

        exams = conn.execute("""
            SELECT
                e.id,
                e.exam_key,
                e.subject,
                e.year,
                e.phase,
                ex.extracted_text,
                cc.extracted_text
            FROM exams e
            JOIN documents ex ON ex.id = e.exam_document_id
            JOIN documents cc ON cc.id = e.criteria_document_id
            WHERE e.phase IN ('F1', 'F2')
            ORDER BY e.year DESC, e.subject, e.phase
        """).fetchall()

        total_blocks = 0

        for exam_id, exam_key, subject, year, phase, exam_text, criteria_text in exams:
            exam_text = clean_text(exam_text or "")
            criteria_text = clean_text(criteria_text or "")

            print(f"A extrair blocos: {exam_key} | {subject}")

            groups = split_groups(exam_text)
            exam_blocks = 0

            for group_name, group_text in groups:
                questions = split_questions(group_text)

                for question_number, raw_statement in questions:
                    raw_criteria = find_criteria_for_question(
                        criteria_text,
                        group_name,
                        question_number
                    )

                    conn.execute("""
                        INSERT INTO question_blocks (
                            exam_id,
                            group_name,
                            question_number,
                            raw_statement,
                            raw_criteria,
                            status,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                        ON CONFLICT(exam_id, group_name, question_number)
                        DO UPDATE SET
                            raw_statement = excluded.raw_statement,
                            raw_criteria = excluded.raw_criteria,
                            status = 'pending',
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        exam_id,
                        group_name,
                        question_number,
                        raw_statement,
                        raw_criteria,
                    ))

                    exam_blocks += 1
                    total_blocks += 1

            print(f"  blocos: {exam_blocks}")

        conn.commit()

    print("")
    print(f"Total de blocos extraídos: {total_blocks}")


if __name__ == "__main__":
    main()