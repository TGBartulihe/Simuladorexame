"""
parser/utils/question_boundaries.py

Módulo NOVO — centraliza a regra de "o que conta como início de uma
questão" num PDF de exame, que antes estava duplicada (com pequenas
variações) em parse_questions.py (QUESTION_PATTERN) e
extract_contexts.py (QUESTION_START).

Motivo da duplicação ser um problema real: ambos os arquivos resolvem o
mesmo problema (achar onde uma questão começa) com regex quase idênticos,
mas escritos separadamente. Se um for corrigido e o outro não, os dois
módulos passam a discordar sobre onde uma questão começa — o que já
estava acontecendo silenciosamente antes desta revisão.

Também resolve dois bugs encontrados na auditoria do banco de dados,
ambos relacionados à tabela de cotações que o IAVE imprime no fim de
cada prova:

  (a) Quando a tabela aparece logo no início do texto de um grupo (antes
      da primeira questão real), ela é capturada como se fosse o
      enunciado da questão 1 — porque a linha "1. 4. 6. 7. ..." bate no
      mesmo padrão textual de início de questão. 22 questões no banco
      atual têm esse defeito.

  (b) Quando a tabela aparece DEPOIS da última questão real de um grupo
      (caso mais comum — ela fica nas últimas páginas do PDF, depois da
      palavra "FIM"), ela fica colada ao FINAL do bloco da última
      questão, porque não há nenhuma questão seguinte para servir de
      delimitador. Isso foi confirmado lendo o PDF original de um exame
      (Biologia e Geologia, 2025, 1.ª fase): a questão real "GRUPO III,
      item 4" tem um enunciado válido, mas o parser concatenava a ele
      toda a tabela "COTAÇÕES" que vem depois do "FIM" da prova.

  truncate_at_exam_end() resolve (b) cortando o texto no marcador "FIM"
  (ou "COTAÇÕES", se "FIM" não existir), ANTES de procurar onde as
  questões começam — assim nenhuma questão chega a "ver" o anexo.
  looks_like_cotacao_table() continua resolvendo (a).
"""
from __future__ import annotations

import re

# Núcleo do padrão: "N." ou "N.M." no início de uma linha, seguido de
# espaço. Usado tanto para achar onde uma questão começa quanto (com o
# match completo) para separar o contexto/cabeçalho do enunciado em si.
QUESTION_NUMBER_CORE = r"(?:[1-9][0-9]?)(?:\.[1-9][0-9]?)?"

QUESTION_START_PATTERN = re.compile(
    rf"(?m)^\s*({QUESTION_NUMBER_CORE})\.\s+"
)

# Uma tabela de cotações tem várias referências numéricas de item na
# MESMA linha (ex: "1. 4. 6. 7. 8. 9. 11. 12. 13. 15.1. 15.2. ...");
# uma questão real tem exatamly uma. > 2 dá uma margem de segurança caso
# algum enunciado real comece citando dois números próximos (raro, mas
# mais seguro que >= 2).
_NUMBER_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)*\.")

# Cabeçalho típico da tabela de cotações da prova, como aparece nos PDFs
# do IAVE: "Cotação (em pontos)" seguida de uma sequência de números.
_COTACAO_TABLE_HEADER_RE = re.compile(
    r"cota[çc][ãa]o\s*\(em pontos\)", re.IGNORECASE
)

# Marcador de fim de prova, usado pelo IAVE antes do anexo de cotações.
# "FIM" sozinho numa linha é o sinal mais confiável; como fallback (caso
# algum PDF não tenha o "FIM" isolado assim), também corta em "COTAÇÕES"
# isolada numa linha — é o título da secção que vem logo depois.
_EXAM_END_MARKER_RE = re.compile(
    r"(?im)^\s*FIM\s*$|^\s*COTA[ÇC][ÕO]ES\s*$"
)


def truncate_at_exam_end(text: str) -> str:
    """Corta `text` no marcador de fim de prova (ver _EXAM_END_MARKER_RE),
    removendo o anexo de cotações que o IAVE imprime depois do "FIM". Se
    nenhum marcador for encontrado, devolve o texto original sem alteração
    (mais seguro não cortar nada do que cortar no lugar errado).
    """
    match = _EXAM_END_MARKER_RE.search(text)
    if not match:
        return text
    return text[: match.start()]


def looks_like_cotacao_table(block: str) -> bool:
    """True se `block` parece ser a tabela-resumo de cotações da prova,
    não o enunciado de uma questão real. Ver docstring do módulo para o
    caso concreto que motivou isto.
    """
    first_line = block.split("\n", 1)[0]
    many_number_tokens = len(_NUMBER_TOKEN_RE.findall(first_line)) > 2
    has_cotacao_header = bool(_COTACAO_TABLE_HEADER_RE.search(block[:300]))
    return many_number_tokens or has_cotacao_header


def find_question_starts(text: str) -> list[re.Match]:
    """Acha todas as posições de início de questão em `text`, já
    excluindo as que na verdade são tabelas de cotação (heurística
    aplicada sobre o trecho até o próximo match, ou até o fim do texto).

    IMPORTANTE: isto NÃO substitui truncate_at_exam_end(). Esta função
    só protege contra o caso (a) da docstring do módulo (tabela no
    início). Quem chama deve truncar o texto do grupo/exame com
    truncate_at_exam_end() ANTES de passar para find_question_starts(),
    para também cobrir o caso (b) (tabela no final, colada à última
    questão) — ver parse_groups.py.
    """
    raw_matches = list(QUESTION_START_PATTERN.finditer(text))
    real_matches = []

    for index, match in enumerate(raw_matches):
        start = match.start()
        end = raw_matches[index + 1].start() if index + 1 < len(raw_matches) else len(text)
        block = text[start:end]

        if looks_like_cotacao_table(block):
            continue

        real_matches.append(match)

    return real_matches
