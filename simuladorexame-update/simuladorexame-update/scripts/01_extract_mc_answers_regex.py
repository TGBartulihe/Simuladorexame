"""
01_extract_mc_answers_regex.py

Extrai o gabarito de questões de escolha múltipla (multiple_choice) a partir
do texto livre em criteria.criteria_text, usando regex, para os casos em que
o padrão é inequívoco.

Padrões cobertos:
  - "Versão 1 – (D); Versão 2 – (B)"   -> duas versões de caderno
  - "Opção (A)" / "Opção \n(A)"         -> versão única
  - Letra solta entre parênteses "(C)" quando há exatamente UMA ocorrência
  - "Item 12. 13.\nVersão 1 (C) (D)\nVersão 2 (D) (B)" -> tabela agregada:
    o parser original juntou o critério de VÁRIAS questões num único
    registro de `criteria`, associado apenas à primeira (ex: question_number
    "12"). As irmãs (question_number "13", "14"...) existem na tabela
    `questions` mas ficaram sem nenhuma linha em `criteria`. Este script
    localiza essas irmãs pelo (exam_id, question_number) e aplica o gabarito
    por posição.

O que este script NÃO resolve (ficam para o script 02, via LLM):
  - criteria_text sem nenhum padrão reconhecível
  - questões de correspondência mal classificadas como multiple_choice
  - texto com glifos corrompidos (extração de fonte simbólica, ex: "/g14")

Importante sobre "Versão 1 / Versão 2": o schema atual (exams.version) está
100% NULL — não há, hoje, registro de qual caderno (1 ou 2) cada aluno real
recebeu. Este script grava AMBAS as opções marcadas como corretas quando há
duas versões, e adiciona uma nota em choices via uma tabela auxiliar de log,
para que a UI possa decidir como exibir isso (ver nota no final do arquivo).

Uso:
    python scripts/01_extract_mc_answers_regex.py --db caminho/para/simuladorexame.db
    python scripts/01_extract_mc_answers_regex.py --db ... --dry-run   # só mostra, não grava
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from dataclasses import dataclass, field


VERSAO_DUPLA_RE = re.compile(
    r"Vers[ãa]o\s*1\s*[–\-—]\s*\(([A-Da-d])\)\s*;\s*Vers[ãa]o\s*2\s*[–\-—]\s*\(([A-Da-d])\)",
    re.IGNORECASE,
)

OPCAO_RE = re.compile(r"Op[çc][ãa]o\s*\(?\s*([A-Da-d])\s*\)?", re.IGNORECASE)

# usado apenas quando o texto não bate nos padrões acima E há exatamente
# uma letra entre parênteses em todo o criteria_text (evita falso-positivo
# em "Item 17. 18. 19. ... (A) (D) (C)" — aí há 3 ocorrências, é ambíguo)
LETRA_SOLTA_RE = re.compile(r"\(([A-Da-d])\)")

# tabela agregada: "Item 12. 13.\nVersão 1 (C) (D)\nVersão 2 (D) (B)"
TABELA_AGREGADA_RE = re.compile(
    r"Item\s+([\d.\s]+?)\s*\n\s*Vers[ãa]o\s*1\s+(.+?)\s*\n\s*Vers[ãa]o\s*2\s+(.+?)(?:\n|$)",
    re.IGNORECASE,
)
LETRAS_EM_SEQUENCIA_RE = re.compile(r"\(([A-Da-d])\)")


@dataclass
class ExtractionResult:
    question_id: int
    pattern: str
    letters: list[str]
    raw_excerpt: str


@dataclass
class Stats:
    total: int = 0
    resolved_versao_dupla: int = 0
    resolved_opcao: int = 0
    resolved_letra_unica: int = 0
    resolved_tabela_agregada: int = 0
    unresolved: int = 0
    letter_not_found_in_choices: list[int] = field(default_factory=list)


def classify(criteria_text: str) -> tuple[str, list[str]] | None:
    if not criteria_text:
        return None

    m = VERSAO_DUPLA_RE.search(criteria_text)
    if m:
        return "versao_dupla", [m.group(1).upper(), m.group(2).upper()]

    m = OPCAO_RE.search(criteria_text)
    if m:
        return "opcao", [m.group(1).upper()]

    matches = LETRA_SOLTA_RE.findall(criteria_text)
    if len(matches) == 1:
        return "letra_unica", [matches[0].upper()]

    return None


@dataclass
class AggregatedRow:
    """Uma posição dentro de uma tabela agregada de gabarito."""

    question_number: str
    letters: list[str]  # 1 letra (versão única) ou 2 (versão 1 e 2)


def classify_aggregated_table(criteria_text: str) -> list[AggregatedRow] | None:
    """Detecta o padrão 'Item N1. N2. ...\\nVersão 1 (L1) (L2)...\\nVersão 2 (L1) (L2)...'
    e devolve uma linha por número de item, com as letras correspondentes
    por posição. Retorna None se o padrão não bater ou se as contagens
    não forem consistentes (melhor não resolver do que resolver errado).
    """
    if not criteria_text:
        return None

    m = TABELA_AGREGADA_RE.search(criteria_text)
    if not m:
        return None

    item_numbers = [n.strip().rstrip(".") for n in m.group(1).split() if n.strip(".")]
    v1_letters = LETRAS_EM_SEQUENCIA_RE.findall(m.group(2))
    v2_letters = LETRAS_EM_SEQUENCIA_RE.findall(m.group(3))

    if not item_numbers:
        return None
    if len(v1_letters) != len(item_numbers) or len(v2_letters) != len(item_numbers):
        # contagem inconsistente — não arrisca associação errada
        return None

    return [
        AggregatedRow(question_number=num, letters=[v1.upper(), v2.upper()])
        for num, v1, v2 in zip(item_numbers, v1_letters, v2_letters)
    ]


def ensure_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mc_answer_extraction_log (
            question_id INTEGER PRIMARY KEY,
            pattern TEXT NOT NULL,
            letters_found TEXT NOT NULL,
            has_dual_version INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'regex',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
        """
    )
    conn.commit()


def apply_letters(
    cur: sqlite3.Cursor, qid: int, letters: list[str], stats: Stats, dry_run: bool
) -> bool:
    """Marca is_correct=1 nas choices de `qid` cujas letras estão em `letters`,
    desde que essas letras existam de fato entre as choices da questão.
    Retorna True se algo foi (ou seria, em dry-run) marcado.
    """
    cur.execute("SELECT letter FROM choices WHERE question_id = ?", (qid,))
    available = {r["letter"].upper() for r in cur.fetchall()}
    valid = [l for l in letters if l in available]

    if not valid:
        stats.letter_not_found_in_choices.append(qid)
        return False

    if dry_run:
        return True

    for letter in valid:
        cur.execute(
            "UPDATE choices SET is_correct = 1 WHERE question_id = ? AND letter = ?",
            (qid, letter),
        )
    return True


def run(db_path: str, dry_run: bool) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not dry_run:
        ensure_log_table(conn)

    stats = Stats()
    resolved_ids: set[int] = set()
    unresolved_samples: list[tuple[int, str]] = []

    # --- Passada 1: tabelas agregadas (uma linha de criteria cobre várias questões) ---
    cur.execute(
        """
        SELECT q.id AS question_id, q.exam_id, c.criteria_text
        FROM questions q
        JOIN criteria c ON c.question_id = q.id
        WHERE q.question_type = 'multiple_choice'
        """
    )
    mc_rows = cur.fetchall()

    for row in mc_rows:
        agg = classify_aggregated_table(row["criteria_text"])
        if not agg:
            continue

        exam_id = row["exam_id"]
        for entry in agg:
            cur.execute(
                """
                SELECT id FROM questions
                WHERE exam_id = ? AND question_number = ? AND question_type = 'multiple_choice'
                """,
                (exam_id, entry.question_number),
            )
            target = cur.fetchone()
            if not target:
                continue
            target_qid = target["id"]

            ok = apply_letters(cur, target_qid, entry.letters, stats, dry_run)
            if ok:
                stats.resolved_tabela_agregada += 1
                resolved_ids.add(target_qid)
                if not dry_run:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO mc_answer_extraction_log
                            (question_id, pattern, letters_found, has_dual_version, source)
                        VALUES (?, 'tabela_agregada', ?, 1, 'regex')
                        """,
                        (target_qid, ",".join(entry.letters)),
                    )

    # --- Passada 2: padrões simples por questão (apenas as ainda não resolvidas) ---
    for row in mc_rows:
        qid = row["question_id"]
        if qid in resolved_ids:
            continue

        result = classify(row["criteria_text"])
        if result is None:
            stats.unresolved += 1
            if len(unresolved_samples) < 10:
                unresolved_samples.append((qid, (row["criteria_text"] or "")[:120]))
            continue

        pattern, letters = result
        if pattern == "versao_dupla":
            stats.resolved_versao_dupla += 1
        elif pattern == "opcao":
            stats.resolved_opcao += 1
        else:
            stats.resolved_letra_unica += 1

        ok = apply_letters(cur, qid, letters, stats, dry_run)
        if ok and not dry_run:
            cur.execute(
                """
                INSERT OR REPLACE INTO mc_answer_extraction_log
                    (question_id, pattern, letters_found, has_dual_version, source)
                VALUES (?, ?, ?, ?, 'regex')
                """,
                (qid, pattern, ",".join(letters), 1 if pattern == "versao_dupla" else 0),
            )

    stats.total = len(mc_rows)

    if not dry_run:
        conn.commit()

    print("=" * 60)
    print("Extração de gabarito (multiple_choice) via regex")
    print("=" * 60)
    print(f"Total de questões multiple_choice com critério: {stats.total}")
    print(f"  Resolvidas — tabela agregada (Item N1 N2...) : {stats.resolved_tabela_agregada}")
    print(f"  Resolvidas — Versão 1/2 explícita .......: {stats.resolved_versao_dupla}")
    print(f"  Resolvidas — 'Opção (X)' .................: {stats.resolved_opcao}")
    print(f"  Resolvidas — letra única sem ambiguidade ..: {stats.resolved_letra_unica}")
    print(f"  Não resolvidas (vão para o script 02/LLM) .: {stats.unresolved}")
    if stats.letter_not_found_in_choices:
        print(
            f"  ATENÇÃO: letra extraída não existe em choices "
            f"para {len(stats.letter_not_found_in_choices)} questões "
            f"(ids: {stats.letter_not_found_in_choices[:10]}...)"
        )
    print("=" * 60)

    if unresolved_samples:
        print("\nAmostra de casos não resolvidos (para conferência manual):")
        for qid, excerpt in unresolved_samples:
            print(f"  question_id={qid}: {excerpt!r}")

    if dry_run:
        print("\n[DRY RUN] Nenhuma alteração foi gravada no banco.")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, help="Caminho para simuladorexame.db")
    parser.add_argument("--dry-run", action="store_true", help="Não grava, só relata")
    args = parser.parse_args()
    run(args.db, args.dry_run)
