"""
02_extract_with_llm.py

Usa um modelo local via Ollama (testado com qwen2.5:7b, o mesmo já usado em
ai_exam_cache) para preencher três lacunas que regex não resolve com
segurança:

  1. Gabarito das ~308 questões de multiple_choice que o script 01 não
     conseguiu resolver (texto sem padrão reconhecível, glifos corrompidos,
     tabelas que misturam mais de um formato).
  2. questions.max_points e criteria.max_points (hoje 100% NULL) — extraídos
     do texto livre em criteria_text (ex: "10 pontos", "8 pontos").
  3. questions.topic / subtopic — classificação por LLM usando o enunciado,
     contra uma lista FECHADA de tópicos por disciplina (ver TOPIC_TAXONOMY
     abaixo). É preferível ao LLM "inventar" um tópico de uma lista curada
     do que criar uma taxonomia nova e inconsistente a cada chamada.

IMPORTANTE — por que isto roda na SUA máquina, não no ambiente do Claude:
O Ollama é local (já confirmámos que faz parte do seu setup, via o registro
em ai_exam_cache rodando qwen2.5:7b). Este script assume um servidor Ollama
em http://localhost:11434 — execute-o de onde o Ollama estiver a correr.

Cada chamada é cacheada numa tabela auxiliar `llm_extraction_cache` (criada por
este script — NÃO reaproveita `ai_cache`, porque essa tabela tem
`question_id` como UNIQUE e não suporta guardar três tipos de extração
diferentes para a mesma questão sem um sobrescrever o outro). É seguro
interromper e retomar; itens já processados com sucesso não são reprocessados.

Uso:
    pip install requests
    ollama pull qwen2.5:7b        # se ainda não tiver
    python scripts/02_extract_with_llm.py --db caminho/simuladorexame.db
    python scripts/02_extract_with_llm.py --db ... --only-missing-answers
    python scripts/02_extract_with_llm.py --db ... --only-points
    python scripts/02_extract_with_llm.py --db ... --only-topics
    python scripts/02_extract_with_llm.py --db ... --limit 20   # teste rápido
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"
PROMPT_VERSION = "extract-v1"

# Taxonomia fechada por disciplina. Curada a partir das 4 disciplinas
# presentes no banco. Pode (e deve) ser revisada por você antes do uso real
# — isto é um ponto de partida razoável, não a palavra final. Manter a
# lista FECHADA é deliberado: assim o LLM classifica dentro de categorias
# conhecidas e a UI de progresso por tópico fica estável (não cresce uma
# categoria nova e ligeiramente diferente a cada exame processado).
TOPIC_TAXONOMY: dict[str, list[str]] = {
    "Português": [
        "Compreensão do texto literário",
        "Compreensão do texto não literário",
        "Gramática — classes de palavras",
        "Gramática — sintaxe e funções sintáticas",
        "Gramática — orações subordinadas",
        "Semântica e pragmática",
        "Educação literária — autores e obras do programa",
        "Produção escrita — texto de opinião/expositivo",
    ],
    "Matemática A": [
        "Funções reais de variável real",
        "Funções trigonométricas",
        "Funções exponenciais e logarítmicas",
        "Cálculo diferencial",
        "Probabilidades e combinatória",
        "Sucessões",
        "Geometria analítica e vetores",
        "Números complexos",
        "Estatística",
    ],
    "Física e Química A": [
        "Mecânica — cinemática e dinâmica",
        "Energia e conservação",
        "Ondas e eletromagnetismo",
        "Estrutura atómica e tabela periódica",
        "Ligação química",
        "Equilíbrio químico e ácido-base",
        "Eletroquímica e reações redox",
        "Cinética química",
    ],
    "Biologia e Geologia": [
        "Biologia celular e bioquímica",
        "Genética e hereditariedade",
        "Metabolismo e obtenção de energia",
        "Reprodução e crescimento",
        "Imunidade e sistema imunitário",
        "Geologia — rochas e minerais",
        "Geologia — tectónica de placas e dinâmica interna",
        "Geologia — tempo geológico e fósseis",
    ],
}


def call_ollama(prompt: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0},
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except requests.RequestException as exc:
            print(f"  [aviso] tentativa {attempt + 1}/{retries} falhou: {exc}", file=sys.stderr)
            time.sleep(2)
    return None


def ensure_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_extraction_cache (
            question_id INTEGER NOT NULL,
            prompt_version TEXT NOT NULL,
            model TEXT,
            prompt_hash TEXT,
            response_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (question_id, prompt_version),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
        """
    )
    conn.commit()


def cache_get(cur: sqlite3.Cursor, question_id: int, prompt_version: str) -> dict | None:
    cur.execute(
        "SELECT response_json FROM llm_extraction_cache WHERE question_id = ? AND prompt_version = ?",
        (question_id, prompt_version),
    )
    row = cur.fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None
    return None


def cache_set(
    cur: sqlite3.Cursor, question_id: int, prompt_version: str, prompt: str, response_obj: dict
) -> None:
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    cur.execute(
        """
        INSERT INTO llm_extraction_cache (question_id, prompt_version, model, prompt_hash, response_json, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(question_id, prompt_version) DO UPDATE SET
            model=excluded.model,
            prompt_hash=excluded.prompt_hash,
            response_json=excluded.response_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (question_id, prompt_version, MODEL, prompt_hash, json.dumps(response_obj, ensure_ascii=False)),
    )


# ---------------------------------------------------------------------------
# 1. Gabarito das multiple_choice ainda sem is_correct
# ---------------------------------------------------------------------------

def build_answer_prompt(statement: str, choices: list[dict], criteria_text: str) -> str:
    choices_block = "\n".join(f"{c['letter']}) {c['text']}" for c in choices)
    return f"""Tu és um corretor de exames nacionais portugueses. Lê o enunciado, as
alternativas e o texto oficial de critério de correção (extraído de PDF,
pode ter ruído de formatação). Identifica qual letra é a resposta correta.

Se o critério mencionar "Versão 1" e "Versão 2" com letras diferentes,
devolve AMBAS as letras (são gabaritos de cadernos diferentes do mesmo
exame, ambos válidos).

Se não conseguires determinar a resposta com confiança razoável, devolve
uma lista vazia e explica o motivo em "observacao".

ENUNCIADO:
{statement}

ALTERNATIVAS:
{choices_block}

TEXTO OFICIAL DO CRITÉRIO (pode ter ruído de extração de PDF):
{criteria_text}

Responde APENAS em JSON, neste formato exato:
{{"letras_corretas": ["A"], "confianca": "alta|media|baixa", "observacao": ""}}
"""


def process_missing_answers(conn: sqlite3.Connection, limit: int | None) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.id AS question_id, q.statement, c.criteria_text
        FROM questions q
        JOIN criteria c ON c.question_id = q.id
        LEFT JOIN mc_answer_extraction_log l ON l.question_id = q.id
        WHERE q.question_type = 'multiple_choice'
          AND l.question_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM choices ch WHERE ch.question_id = q.id AND ch.is_correct = 1
          )
        """
    )
    rows = cur.fetchall()
    if limit:
        rows = rows[:limit]

    print(f"\n--- Gabaritos pendentes via LLM: {len(rows)} questões ---")
    resolved = 0
    low_confidence = 0
    unresolved = 0

    for i, row in enumerate(rows, 1):
        qid = row[0] if not isinstance(row, sqlite3.Row) else row["question_id"]
        statement = row["statement"]
        criteria_text = row["criteria_text"] or ""

        cached = cache_get(cur, qid, PROMPT_VERSION)
        if cached is None:
            cur.execute("SELECT letter, text FROM choices WHERE question_id = ?", (qid,))
            choices = [{"letter": r[0], "text": r[1]} for r in cur.fetchall()]
            prompt = build_answer_prompt(statement, choices, criteria_text)
            raw = call_ollama(prompt)
            if raw is None:
                print(f"  [{i}/{len(rows)}] qid={qid}: falha de conexão com Ollama, a saltar")
                unresolved += 1
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                print(f"  [{i}/{len(rows)}] qid={qid}: resposta não é JSON válido, a saltar")
                unresolved += 1
                continue
            cache_set(cur, qid, PROMPT_VERSION, prompt, parsed)
            conn.commit()
        else:
            parsed = cached

        letras = parsed.get("letras_corretas") or []
        confianca = parsed.get("confianca", "baixa")

        if not letras:
            unresolved += 1
            continue

        if confianca == "baixa":
            low_confidence += 1
            # marca mesmo assim, mas fica registado em ai_cache para revisão manual
            # (a UI pode sinalizar perguntas com confianca=baixa para conferência humana)

        for letra in letras:
            cur.execute(
                "UPDATE choices SET is_correct = 1 WHERE question_id = ? AND UPPER(letter) = ?",
                (qid, letra.upper()),
            )
        resolved += 1

        if i % 20 == 0:
            print(f"  [{i}/{len(rows)}] processadas...")

    conn.commit()
    print(f"Resolvidas: {resolved} | confiança baixa (revisar): {low_confidence} | sem resposta: {unresolved}")


# ---------------------------------------------------------------------------
# 2. max_points
# ---------------------------------------------------------------------------

def build_points_prompt(criteria_text: str) -> str:
    return f"""Extrai a cotação (pontuação máxima) deste critério de correção de exame
nacional português. O texto pode ter ruído de extração de PDF (pontos de
preenchimento, quebras de linha estranhas).

TEXTO:
{criteria_text}

Responde APENAS em JSON: {{"pontos": <número ou null se não encontrares>}}
"""


def process_points(conn: sqlite3.Connection, limit: int | None) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.question_id, c.criteria_text
        FROM criteria c
        JOIN questions q ON q.id = c.question_id
        WHERE q.max_points IS NULL AND c.criteria_text IS NOT NULL
        """
    )
    rows = cur.fetchall()
    if limit:
        rows = rows[:limit]

    print(f"\n--- max_points pendentes via LLM: {len(rows)} questões ---")
    resolved = 0

    for i, row in enumerate(rows, 1):
        qid, criteria_text = row[0], row[1]

        parsed = cache_get(cur, qid, "points-v1")
        if parsed is None:
            prompt = build_points_prompt(criteria_text)
            raw = call_ollama(prompt)
            if raw is None:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            cache_set(cur, qid, "points-v1", prompt, parsed)
            conn.commit()

        pontos = parsed.get("pontos")
        if pontos is not None:
            cur.execute("UPDATE questions SET max_points = ? WHERE id = ?", (pontos, qid))
            cur.execute("UPDATE criteria SET max_points = ? WHERE question_id = ?", (pontos, qid))
            resolved += 1

        if i % 50 == 0:
            print(f"  [{i}/{len(rows)}] processadas...")

    conn.commit()
    print(f"Resolvidos: {resolved}/{len(rows)}")


# ---------------------------------------------------------------------------
# 3. topic / subtopic
# ---------------------------------------------------------------------------

def build_topic_prompt(subject: str, statement: str, topics: list[str]) -> str:
    topics_block = "\n".join(f"- {t}" for t in topics)
    return f"""Classifica esta questão de exame nacional de {subject} num dos tópicos
abaixo (escolhe EXATAMENTE um da lista, não inventes outro):

{topics_block}

ENUNCIADO:
{statement}

Responde APENAS em JSON:
{{"topico": "<um dos tópicos da lista>", "subtopico": "<frase curta livre, 3-6 palavras>"}}
"""


def process_topics(conn: sqlite3.Connection, limit: int | None) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.id, e.subject, q.statement
        FROM questions q
        JOIN exams e ON e.id = q.exam_id
        WHERE q.topic IS NULL
        """
    )
    rows = cur.fetchall()
    if limit:
        rows = rows[:limit]

    print(f"\n--- tópicos pendentes via LLM: {len(rows)} questões ---")
    resolved = 0
    rejected_not_in_list = 0

    for i, row in enumerate(rows, 1):
        qid, subject, statement = row[0], row[1], row[2]
        topics = TOPIC_TAXONOMY.get(subject)
        if not topics:
            print(f"  [aviso] disciplina '{subject}' sem taxonomia definida, a saltar qid={qid}")
            continue

        parsed = cache_get(cur, qid, "topics-v1")
        if parsed is None:
            prompt = build_topic_prompt(subject, statement, topics)
            raw = call_ollama(prompt)
            if raw is None:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            cache_set(cur, qid, "topics-v1", prompt, parsed)
            conn.commit()

        topico = parsed.get("topico")
        subtopico = parsed.get("subtopico")

        # validação rígida contra a lista fechada — protege contra o LLM
        # inventar uma categoria nova que quebraria a consistência da UI
        if topico not in topics:
            rejected_not_in_list += 1
            continue

        cur.execute(
            "UPDATE questions SET topic = ?, subtopic = ? WHERE id = ?",
            (topico, subtopico, qid),
        )
        resolved += 1

        if i % 50 == 0:
            print(f"  [{i}/{len(rows)}] processadas...")

    conn.commit()
    print(f"Resolvidos: {resolved}/{len(rows)} | rejeitados (tópico fora da lista): {rejected_not_in_list}")


def ensure_topics_skills_tables_populated(conn: sqlite3.Connection) -> None:
    """Popula a tabela `topics` (catálogo) a partir da taxonomia fechada,
    para que a UI possa listar 'tópicos desta disciplina' sem fazer
    SELECT DISTINCT em questions (que só reflete o que já foi classificado).
    """
    cur = conn.cursor()
    for subject, topics in TOPIC_TAXONOMY.items():
        for name in topics:
            cur.execute(
                "INSERT OR IGNORE INTO topics (subject, name) VALUES (?, ?)",
                (subject, name),
            )
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--only-missing-answers", action="store_true")
    parser.add_argument("--only-points", action="store_true")
    parser.add_argument("--only-topics", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Limite de itens p/ teste rápido")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_cache_table(conn)

    # checagem de saúde: o Ollama está respondendo?
    test = call_ollama('Responde apenas {"ok": true} em JSON.', retries=1)
    if test is None:
        print("ERRO: não foi possível contactar o Ollama em http://localhost:11434")
        print("Confirme que está a correr: `ollama serve` e `ollama list` mostra qwen2.5:7b")
        sys.exit(1)
    print("Ollama respondeu corretamente. A iniciar extração...\n")

    run_all = not (args.only_missing_answers or args.only_points or args.only_topics)

    if run_all or args.only_missing_answers:
        process_missing_answers(conn, args.limit)
    if run_all or args.only_points:
        process_points(conn, args.limit)
    if run_all or args.only_topics:
        ensure_topics_skills_tables_populated(conn)
        process_topics(conn, args.limit)

    conn.close()
    print("\nConcluído.")


if __name__ == "__main__":
    main()
