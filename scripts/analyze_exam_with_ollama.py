import json
import hashlib
import sqlite3
import requests
from pathlib import Path

DB_PATH = Path("database/simuladorexame.db")
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
PROMPT_VERSION = "ollama-exam-cache-v1"


def ensure_cache_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_exam_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL UNIQUE,
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
    """)


def get_exam(conn, exam_key):
    row = conn.execute("""
        SELECT
            e.id,
            e.exam_key,
            e.year,
            e.subject,
            e.code,
            e.phase,
            ex.extracted_text,
            cc.extracted_text
        FROM exams e
        JOIN documents ex ON ex.id = e.exam_document_id
        JOIN documents cc ON cc.id = e.criteria_document_id
        WHERE e.exam_key = ?
    """, (exam_key,)).fetchone()

    if not row:
        raise ValueError(f"Exame não encontrado: {exam_key}")

    return {
        "exam_id": row[0],
        "exam_key": row[1],
        "year": row[2],
        "subject": row[3],
        "code": row[4],
        "phase": row[5],
        "exam_text": row[6] or "",
        "criteria_text": row[7] or "",
    }


def input_hash(exam):
    raw = exam["exam_key"] + exam["exam_text"] + exam["criteria_text"]
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def trim_text(text, max_chars):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCADO PARA TESTE INICIAL]"


def build_prompt(exam):
    # Primeiro teste: limitado para não esmagar o notebook.
    exam_text = trim_text(exam["exam_text"], 18000)
    criteria_text = trim_text(exam["criteria_text"], 14000)

    return f"""
Tu és um assistente especializado em exames nacionais portugueses.

Tarefa:
Analisa o enunciado e os critérios de classificação abaixo e devolve APENAS JSON válido.

Objetivo:
Criar uma versão estruturada e cacheável deste exame para uma aplicação de simulação.

Metadados:
- exam_key: {exam["exam_key"]}
- subject: {exam["subject"]}
- code: {exam["code"]}
- year: {exam["year"]}
- phase: {exam["phase"]}

JSON obrigatório:
{{
  "exam_key": "{exam["exam_key"]}",
  "subject": "{exam["subject"]}",
  "code": "{exam["code"]}",
  "year": {exam["year"]},
  "phase": "{exam["phase"]}",
  "questions": [
    {{
      "number": "1",
      "group": "Grupo I",
      "statement": "texto da pergunta",
      "question_type": "multiple_choice | short_answer | open_answer | calculation | essay | unknown",
      "choices": [
        {{"label": "A", "text": "opção A"}},
        {{"label": "B", "text": "opção B"}}
      ],
      "correct_answer": "resposta correta ou null",
      "official_criteria": "critério oficial correspondente ou null",
      "max_score": null,
      "topic": "tema/conteúdo",
      "pedagogical_explanation": "explicação curta para o aluno"
    }}
  ],
  "warnings": []
}}

Regras:
- Não inventes critérios oficiais.
- Se não conseguires identificar algo, usa null.
- Para perguntas abertas, correct_answer deve ser null e official_criteria deve conter a rubrica.
- Para escolha múltipla, tenta identificar a alternativa correta nos critérios.
- Mantém tudo em português europeu.
- Devolve apenas JSON válido.

ENUNCIADO:
{exam_text}

CRITÉRIOS:
{criteria_text}
"""


def call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=600)
    response.raise_for_status()
    data = response.json()
    return data["response"]


def save_cache(conn, exam_id, status, h, structured_json=None, error=None):
    conn.execute("""
        INSERT INTO ai_exam_cache (
            exam_id,
            status,
            model,
            prompt_version,
            input_hash,
            structured_json,
            error_message,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(exam_id) DO UPDATE SET
            status = excluded.status,
            model = excluded.model,
            prompt_version = excluded.prompt_version,
            input_hash = excluded.input_hash,
            structured_json = excluded.structured_json,
            error_message = excluded.error_message,
            updated_at = CURRENT_TIMESTAMP
    """, (
        exam_id,
        status,
        OLLAMA_MODEL,
        PROMPT_VERSION,
        h,
        structured_json,
        error,
    ))


def main():
    exam_key = "2025-702-F1"

    with sqlite3.connect(DB_PATH) as conn:
        ensure_cache_table(conn)

        exam = get_exam(conn, exam_key)
        h = input_hash(exam)

        print(f"A analisar: {exam_key}")
        print(f"Enunciado: {len(exam['exam_text'])} caracteres")
        print(f"Critérios: {len(exam['criteria_text'])} caracteres")

        try:
            prompt = build_prompt(exam)
            raw_json = call_ollama(prompt)

            parsed = json.loads(raw_json)

            pretty_json = json.dumps(parsed, ensure_ascii=False, indent=2)

            save_cache(
                conn,
                exam["exam_id"],
                "success",
                h,
                structured_json=pretty_json
            )

            conn.commit()

            print("Cache IA criado com sucesso.")
            print(f"Questões encontradas: {len(parsed.get('questions', []))}")

        except Exception as e:
            save_cache(conn, exam["exam_id"], "failed", h, error=str(e))
            conn.commit()
            print(f"Erro: {e}")


if __name__ == "__main__":
    main()