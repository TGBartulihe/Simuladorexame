import os
import json
import hashlib
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

DB_PATH = Path("database/simuladorexame.db")
PROMPT_VERSION = "exam-analysis-v1"

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_exam(conn, exam_key):
    row = conn.execute("""
        SELECT
            e.id,
            e.exam_key,
            e.year,
            e.subject,
            e.code,
            e.phase,
            ex.extracted_text AS exam_text,
            cc.extracted_text AS criteria_text
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
        "exam_text": row[6],
        "criteria_text": row[7],
    }


def hash_input(exam):
    payload = f"{exam['exam_key']}|{exam['exam_text']}|{exam['criteria_text']}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_prompt(exam):
    return f"""
Analisa este exame nacional português e os respetivos critérios de classificação.

Objetivo:
Transformar o exame em JSON estruturado para uma aplicação de simulação de exame.

Disciplina: {exam['subject']}
Código: {exam['code']}
Ano: {exam['year']}
Fase: {exam['phase']}
Chave: {exam['exam_key']}

Deves devolver APENAS JSON válido, sem markdown.

Estrutura obrigatória:

{{
  "exam_key": "...",
  "subject": "...",
  "code": "...",
  "year": 2025,
  "phase": "F1",
  "summary": "...",
  "questions": [
    {{
      "number": "1",
      "group": "Grupo I",
      "statement": "...",
      "question_type": "multiple_choice | short_answer | open_answer | calculation | essay | unknown",
      "choices": [
        {{"label": "A", "text": "..."}},
        {{"label": "B", "text": "..."}}
      ],
      "correct_answer": "...",
      "official_criteria": "...",
      "max_score": null,
      "topic": "...",
      "skills": ["..."],
      "pedagogical_explanation": "...",
      "correction_guidance": "..."
    }}
  ],
  "warnings": [
    "Indica aqui ambiguidades, informação incompleta ou problemas de extração."
  ]
}}

Regras:
- Não inventes respostas se os critérios não forem claros.
- Quando não souberes, usa null ou "unknown".
- Mantém os critérios oficiais separados da explicação pedagógica.
- Para perguntas abertas, não forces uma resposta única; cria uma rubrica de correção.
- Para escolha múltipla, tenta identificar a resposta correta a partir dos critérios.
- Preserva a numeração real do exame.

ENUNCIADO:
{exam['exam_text']}

CRITÉRIOS:
{exam['criteria_text']}
"""


def analyze_with_ai(prompt):
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        text={
            "format": {
                "type": "json_object"
            }
        }
    )

    return response.output_text


def save_cache(conn, exam_id, model, input_hash, structured_json, status="success", error=None):
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
        model,
        PROMPT_VERSION,
        input_hash,
        structured_json,
        error,
    ))


def main():
    # Começa com um exame só.
    exam_key = "2025-702-F1"

    with sqlite3.connect(DB_PATH) as conn:
        exam = get_exam(conn, exam_key)
        input_hash = hash_input(exam)

        existing = conn.execute("""
            SELECT status, input_hash
            FROM ai_exam_cache
            WHERE exam_id = ?
        """, (exam["exam_id"],)).fetchone()

        if existing and existing[0] == "success" and existing[1] == input_hash:
            print(f"Cache já existe e está atualizado para {exam_key}")
            return

        print(f"A analisar com IA: {exam_key}")

        try:
            prompt = build_prompt(exam)
            structured_json = analyze_with_ai(prompt)

            # valida JSON
            json.loads(structured_json)

            save_cache(
                conn,
                exam["exam_id"],
                MODEL,
                input_hash,
                structured_json,
                status="success"
            )

            conn.commit()
            print("Análise IA guardada em cache com sucesso.")

        except Exception as e:
            save_cache(
                conn,
                exam["exam_id"],
                MODEL,
                input_hash,
                None,
                status="failed",
                error=str(e)
            )
            conn.commit()
            print(f"Erro na análise IA: {e}")


if __name__ == "__main__":
    main()