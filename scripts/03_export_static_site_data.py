"""
03_export_static_site_data.py

Lê simuladorexame.db e gera os JSON estáticos consumidos pelo frontend,
seguindo a arquitetura descrita no README do repositório:
  SQLite -> JSON estáticos -> app/ (React/Vite, publicado no GitHub Pages)

Saída (em --out, padrão app/public/data/):
  catalog.json
      Lista de disciplinas, anos e fases disponíveis — alimenta o menu de
      seleção sem precisar carregar todos os exames de uma vez.

  exams/{exam_key}.json  (um arquivo por exame)
      Estrutura completa do exame: grupos, contextos, questões, alternativas
      e gabarito. Carregado sob demanda quando o aluno escolhe um exame.

  topics/{subject}.json  (um arquivo por disciplina)
      Catálogo de tópicos da disciplina (da tabela `topics`, populada pelo
      script 02) — usado para mostrar a lista de assuntos possíveis mesmo
      antes de o aluno ter respondido nada.

Nota sobre dados incompletos (ver scripts 01 e 02): perguntas de
multiple_choice sem nenhuma choice com is_correct=1, ou sem max_points,
são marcadas explicitamente com "gabarito_disponivel": false /
"pontuacao_disponivel": false no JSON, para a UI tratar com um estado
visual honesto em vez de fingir um zero.

Nota sobre statements corrompidos (achado durante a validação deste export,
22 questões na base atual): em provas com "grupo de escolha" (ex: "destes
8 itens, contam para a nota final os 4 com melhor pontuação", comum em
Biologia e Geologia / Física e Química A), a tabela-resumo de cotações que
o PDF imprime ANTES do primeiro enunciado foi capturada pelo parser como se
fosse o texto da questão 1. O statement nesses casos é só números e a
palavra "Cotação" — não há enunciado real ali. Isto não tem correção segura
no export: a questão real provavelmente está perdida ou precisa ser
reextraída do PDF original. Este script detecta o padrão e exporta com
"statementCorrompido": true, para a UI excluir essas questões da simulação
em vez de mostrar uma "pergunta" sem sentido ao aluno. Recomendo registar
isto como item de correção no pipeline `process_parser_v2` / `ParserPipeline`
(provavelmente a etapa que separa o cabeçalho de cotações do primeiro bloco
de enunciado precisa de um corte mais cedo).

Uso:
    python scripts/03_export_static_site_data.py --db simuladorexame.db --out app/public/data
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path


# tabela-resumo de cotações da prova capturada por engano como statement
# da primeira questão (ver nota no topo do arquivo) — padrão: o texto
# começa direto com uma sequência de números/pontos seguida da palavra
# "Cotação", sem nenhuma frase de enunciado antes.
CORRUPTED_STATEMENT_RE = re.compile(r"^[\d\.\s]+\nCota[çc][ãa]o", re.IGNORECASE)


def is_statement_corrupted(statement: str | None) -> bool:
    if not statement:
        return False
    return bool(CORRUPTED_STATEMENT_RE.match(statement))


def slugify(text: str) -> str:
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    lowered = text.lower()
    for accented, plain in replacements.items():
        lowered = lowered.replace(accented, plain)
    return "-".join(lowered.split())


def build_catalog_from_exported_exams(out_dir: Path) -> dict:
    """Deriva o catálogo a partir dos JSONs de exame já exportados, em vez
    de recalcular as mesmas regras em SQL puro. Isto garante que a contagem
    de "questões disponíveis" no menu (catalog.json) usa exatamente a mesma
    definição de "questão válida" que a tela de simulação vai aplicar —
    incluindo a exclusão de statements corrompidos (ver nota no topo do
    arquivo). Duas fontes de verdade para a mesma regra é como esse tipo de
    inconsistência (o "completo" falso que corrigimos) volta a aparecer.
    """
    exams_dir = out_dir / "exams"
    subjects: dict[str, dict] = {}

    for exam_file in sorted(exams_dir.glob("*.json")):
        exam = json.loads(exam_file.read_text(encoding="utf-8"))
        # .get(..., False) em vez de [...] — protege contra arquivo .json
        # de uma versão antiga do script que não tinha este campo (ver
        # correção em export_all_exams, que agora limpa a pasta antes de
        # regenerar; isto aqui é uma segunda camada de segurança, não a
        # correção principal).
        usable_questions = [q for q in exam["questions"] if not q.get("statementCorrompido", False)]
        total = len(usable_questions)

        mc_questions = [q for q in usable_questions if q.get("question_type") == "multiple_choice"]
        mc_with_answer = sum(1 for q in mc_questions if q.get("gabaritoDisponivel", False))
        with_points = sum(1 for q in usable_questions if q.get("pontuacaoDisponivel", False))

        if total == 0:
            completeness = "sem_questoes_extraidas"
        else:
            completeness = "completo"
            if mc_questions and mc_with_answer < len(mc_questions):
                completeness = "gabarito_parcial"
            if with_points < total:
                completeness = "pontuacao_parcial" if completeness == "completo" else "incompleto"

        # scripts/triage_exams.py (rodado separadamente) marca exames com
        # contagem atípica, poucos grupos, ou saltos de numeração grandes
        # — sinais de possível perda de dados na extração que os outros
        # critérios de completeness (gabarito/pontuação) não cobrem. Não
        # sobrescreve "sem_questoes_extraidas" (que já é o pior caso).
        triage_status = exam.get("triageStatus", "nao_triado")
        if triage_status == "revisar" and completeness != "sem_questoes_extraidas":
            completeness = "revisar_extracao"

        subject = exam["subject"]
        subjects.setdefault(subject, {"subject": subject, "slug": slugify(subject), "years": {}})
        year_bucket = subjects[subject]["years"].setdefault(str(exam["year"]), [])
        year_bucket.append(
            {
                "examId": exam["examId"],
                "examKey": exam["examKey"],
                "phase": exam["phase"],
                "totalQuestions": total,
                "completeness": completeness,
            }
        )

    return {
        "subjects": [
            {
                "subject": data["subject"],
                "slug": data["slug"],
                "years": [
                    {"year": int(year), "exams": exams}
                    for year, exams in sorted(data["years"].items(), key=lambda kv: -int(kv[0]))
                ],
            }
            for data in subjects.values()
        ]
    }


def export_catalog(out_dir: Path) -> None:
    catalog = build_catalog_from_exported_exams(out_dir)
    total_exams = sum(
        len(year["exams"]) for subject in catalog["subjects"] for year in subject["years"]
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"catalog.json gerado com {total_exams} exames em {len(catalog['subjects'])} disciplinas")


def export_exam(conn: sqlite3.Connection, exam_row: sqlite3.Row, out_dir: Path) -> None:
    cur = conn.cursor()
    exam_id = exam_row["id"]

    cur.execute(
        "SELECT id, group_name, display_order, context_text FROM groups_table WHERE exam_id = ? ORDER BY display_order",
        (exam_id,),
    )
    groups = {g["id"]: dict(g) for g in cur.fetchall()}

    cur.execute(
        "SELECT id, group_id, context_key, title, raw_text FROM question_contexts WHERE exam_id = ?",
        (exam_id,),
    )
    contexts = {c["id"]: dict(c) for c in cur.fetchall()}

    cur.execute(
        """
        SELECT id, group_id, context_id, question_number, statement, question_type,
               max_points, difficulty, bloom_level, topic, subtopic, estimated_minutes
        FROM questions WHERE exam_id = ?
        ORDER BY CAST(
            REPLACE(REPLACE(question_number, '.', ''), ' ', '') AS INTEGER
        ), question_number
        """,
        (exam_id,),
    )
    question_rows = cur.fetchall()

    questions = []
    for q in question_rows:
        qid = q["id"]
        item = dict(q)

        cur.execute(
            "SELECT id, letter, text, is_correct FROM choices WHERE question_id = ? ORDER BY letter",
            (qid,),
        )
        choice_rows = [dict(c) for c in cur.fetchall()]
        has_marked_answer = any(c["is_correct"] for c in choice_rows)

        cur.execute(
            "SELECT criteria_text, max_points, official_answer FROM criteria WHERE question_id = ?",
            (qid,),
        )
        criteria_row = cur.fetchone()

        item["choices"] = [
            {"id": c["id"], "letter": c["letter"], "text": c["text"], "isCorrect": bool(c["is_correct"])}
            for c in choice_rows
        ] if choice_rows else None

        item["criteriaText"] = criteria_row["criteria_text"] if criteria_row else None
        item["officialAnswer"] = criteria_row["official_answer"] if criteria_row else None

        # flags explícitos de completude — a UI decide o que mostrar
        # em vez de a ausência de dado ser silenciosamente tratada como "errado"
        item["gabaritoDisponivel"] = (
            has_marked_answer if q["question_type"] == "multiple_choice" else bool(criteria_row)
        )
        item["pontuacaoDisponivel"] = q["max_points"] is not None
        item["statementCorrompido"] = is_statement_corrupted(q["statement"])

        item["groupName"] = groups.get(q["group_id"], {}).get("group_name")
        ctx = contexts.get(q["context_id"])
        item["contextTitle"] = ctx["title"] if ctx else None
        item["contextText"] = ctx["raw_text"] if ctx else None

        # remove chaves internas que a UI não precisa duplicada (já está em contextTitle/contextText)
        del item["group_id"]
        del item["context_id"]

        questions.append(item)

    exam_json = {
        "examId": exam_id,
        "examKey": exam_row["exam_key"],
        "subject": exam_row["subject"],
        "year": exam_row["year"],
        "phase": exam_row["phase"],
        "triageStatus": _get_triage_status(cur, exam_id),
        "groups": [
            {"id": gid, "name": g["group_name"], "order": g["display_order"]}
            for gid, g in sorted(groups.items(), key=lambda kv: kv[1]["display_order"])
        ],
        "questions": questions,
    }

    exams_dir = out_dir / "exams"
    exams_dir.mkdir(parents=True, exist_ok=True)
    (exams_dir / f"{exam_row['exam_key']}.json").write_text(
        json.dumps(exam_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _get_triage_status(cur: sqlite3.Cursor, exam_id: int) -> str:
    """Lê o status de scripts/triage_exams.py ('bom' ou 'revisar'), se
    essa triagem já tiver rodado. Se a tabela exam_triage não existir
    ainda (triagem nunca rodou), devolve 'nao_triado' — a UI trata isso
    como "bom" por padrão, sem bloquear nada, mas o valor explícito
    permite diferenciar depois.
    """
    try:
        cur.execute("SELECT status FROM exam_triage WHERE exam_id = ?", (exam_id,))
        row = cur.fetchone()
        return row["status"] if row else "nao_triado"
    except sqlite3.OperationalError:
        return "nao_triado"


def export_all_exams(conn: sqlite3.Connection, out_dir: Path) -> None:
    cur = conn.cursor()
    cur.execute("SELECT id, exam_key, subject, year, phase FROM exams")
    exam_rows = cur.fetchall()

    # CORREÇÃO — bug real: rodar este script mais de uma vez (comum
    # durante o desenvolvimento/depuração) deixava arquivos .json de
    # execuções ANTERIORES na pasta exams/, de versões do script que não
    # tinham os mesmos campos (ex: "statementCorrompido" foi adicionado
    # numa correção posterior). build_catalog_from_exported_exams() lê
    # TODOS os .json da pasta, então um arquivo órfão de versão antiga
    # quebrava o catálogo inteiro com KeyError. Limpar a pasta antes de
    # gerar de novo garante que ela reflita só a execução atual.
    exams_dir = out_dir / "exams"
    if exams_dir.exists():
        removed = 0
        for old_file in exams_dir.glob("*.json"):
            old_file.unlink()
            removed += 1
        if removed:
            print(f"Removidos {removed} arquivo(s) .json antigos de {exams_dir} antes de regenerar.")

    for row in exam_rows:
        export_exam(conn, row, out_dir)
    print(f"{len(exam_rows)} arquivos de exame gerados em {exams_dir}")


def export_topics(conn: sqlite3.Connection, out_dir: Path) -> None:
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT subject FROM topics")
    subjects = [r[0] for r in cur.fetchall()]

    topics_dir = out_dir / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)

    for subject in subjects:
        cur.execute("SELECT name FROM topics WHERE subject = ? ORDER BY name", (subject,))
        names = [r[0] for r in cur.fetchall()]
        (topics_dir / f"{slugify(subject)}.json").write_text(
            json.dumps({"subject": subject, "topics": names}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"{len(subjects)} catálogos de tópicos gerados em {topics_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", default="app/public/data")
    args = parser.parse_args()

    out_dir = Path(args.out)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    export_all_exams(conn, out_dir)
    export_catalog(out_dir)
    export_topics(conn, out_dir)

    conn.close()
    print("\nExport concluído.")


if __name__ == "__main__":
    main()
