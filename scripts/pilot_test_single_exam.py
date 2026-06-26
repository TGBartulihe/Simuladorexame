"""
pilot_test_single_exam.py — teste piloto (não faz parte do pipeline
normal). Roda o parser CORRIGIDO contra um único par de PDFs (prova +
critério) já escolhido, sem tocar no banco principal, e imprime um
relatório comparando com o que já está gravado em questions/criteria
para esse mesmo exame — para você conferir visualmente se a correção
funcionou antes de reprocessar os 396 documentos inteiros.

Como funciona: usa as mesmas funções de extração/parsing do pipeline
real (extract_pdf, parse_groups, parse_questions corrigido,
parse_criteria corrigido), mas grava o resultado num banco SQLite
TEMPORÁRIO em memória — nunca toca em database/simuladorexame.db.

Uso:
    python scripts/pilot_test_single_exam.py --exam-pdf "storage/pdfs/EX-BG702-F1-2025-V1_net.pdf" --criteria-pdf "storage/pdfs/EX-BG702-F1-2025-CC-VD_net.pdf"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# garante que 'parser' (o pacote do projeto) é importável a partir da raiz do repo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser.extract.extract_pdf import PDFExtractor
from parser.utils.clean_text import clean_text
from parser.utils.split_pages import split_pages
from parser.parse.parse_groups import parse_groups
from parser.parse.parse_questions import QuestionParser
from parser.extract.extract_contexts import extract_contexts
from parser.parse.parse_criteria import parse_criteria
from parser.utils.match_questions import match_questions


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--exam-pdf", required=True)
    arg_parser.add_argument("--criteria-pdf", required=True)
    args = arg_parser.parse_args()

    exam_pdf = Path(args.exam_pdf)
    criteria_pdf = Path(args.criteria_pdf)

    print(f"Extraindo texto de: {exam_pdf.name}")
    extractor = PDFExtractor()
    exam_text = extractor.extract(exam_pdf)
    if extractor.warnings:
        print(f"  ATENÇÃO: {len(extractor.warnings)} aviso(s) de qualidade na extração:")
        for w in extractor.warnings:
            print(f"    - {w.detail}")

    print(f"Extraindo texto de: {criteria_pdf.name}")
    criteria_extractor = PDFExtractor()
    criteria_text_raw = criteria_extractor.extract(criteria_pdf)
    if criteria_extractor.warnings:
        print(f"  ATENÇÃO: {len(criteria_extractor.warnings)} aviso(s) de qualidade na extração:")
        for w in criteria_extractor.warnings:
            print(f"    - {w.detail}")

    print()
    print("=" * 70)
    print("Processando com o pipeline corrigido...")
    print("=" * 70)

    exam_text = clean_text(exam_text)
    criteria_text = clean_text(criteria_text_raw)

    exam_pages = split_pages(exam_text)
    criteria_pages = split_pages(criteria_text)

    groups = parse_groups(exam_id=0, pages=exam_pages)
    print(f"\nGrupos encontrados: {[g.name for g in groups]}")

    # DIAGNÓSTICO EXTRA: salva o texto bruto de cada grupo (já truncado
    # por parse_groups, mas antes de qualquer outra coisa) num arquivo,
    # para inspecionar exatamente onde truncate_at_exam_end() cortou.
    debug_dir = Path("debug_pilot_output")
    debug_dir.mkdir(exist_ok=True)
    for group in groups:
        safe_name = group.name.replace(" ", "_")
        out_path = debug_dir / f"{safe_name}_{group.order}.txt"
        out_path.write_text(group.text, encoding="utf-8")
    print(f"  (texto bruto de cada grupo salvo em {debug_dir}/ para inspeção)")

    question_parser = QuestionParser()
    questions = question_parser.parse(exam_id=0, groups=groups)
    print(f"\nQuestões encontradas: {len(questions)}")
    for q in questions:
        preview = q.statement.strip().replace("\n", " ")[:80]
        print(f"  [{q.number:>6}] ({q.metadata['question_type']:<15}) {preview}...")

    # DIAGNÓSTICO EXTRA: para cada grupo, mostra os matches BRUTOS de
    # find_question_starts (antes do filtro _is_valid_question), para
    # achar questões que "desapareceram" entre a detecção e a validação.
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO: matches brutos por grupo (antes de _is_valid_question)")
    print("=" * 70)
    from parser.utils.question_boundaries import find_question_starts
    for group in groups:
        raw_matches = find_question_starts(group.text)
        print(f"\n{group.name} ({len(group.text)} chars no grupo): {len(raw_matches)} matches brutos")
        for i, m in enumerate(raw_matches):
            start = m.start()
            end = raw_matches[i + 1].start() if i + 1 < len(raw_matches) else len(group.text)
            block = group.text[start:end].strip()
            status = "OK" if len(block) >= 120 else "DESCARTADO (curto)"
            print(f"    numero={m.group(1):>6} len={len(block):>5} [{status}] {block[:60]!r}")

    criteria = parse_criteria(criteria_pages)
    print(f"\nCritérios encontrados: {len(criteria)} (números: {sorted(criteria.keys())})")

    # DIAGNÓSTICO EXTRA: salva o texto bruto do critério (já limpo por
    # clean_text, antes do parse_criteria) para inspecionar exatamente
    # o que o parse_criteria está vendo, sem reconstrução manual.
    debug_dir.mkdir(exist_ok=True)
    (debug_dir / "criteria_raw.txt").write_text(criteria_text, encoding="utf-8")
    print(f"  (texto bruto do critério salvo em {debug_dir}/criteria_raw.txt)")

    # checagem específica: alguma questão sem critério correspondente?
    question_numbers = {q.number for q in questions}
    criteria_numbers = set(criteria.keys())
    missing_criteria = question_numbers - criteria_numbers
    if missing_criteria:
        print(f"\n  Questões SEM critério correspondente: {sorted(missing_criteria)}")
    else:
        print("\n  Todas as questões têm critério correspondente. ✓")

    # checagem específica: alguma questão com statement suspeito de ser
    # tabela de cotações (o bug que corrigimos)?
    suspicious = [q for q in questions if "cotação" in q.statement.lower() and len(q.statement) < 400]
    if suspicious:
        print(f"\n  ATENÇÃO: {len(suspicious)} questão(ões) com statement suspeito (mencionam 'cotação'):")
        for q in suspicious:
            print(f"    [{q.number}] {q.statement[:100]!r}")
    else:
        print("  Nenhum statement suspeito de ser tabela de cotações. ✓")


if __name__ == "__main__":
    main()
