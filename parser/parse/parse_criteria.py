from __future__ import annotations

import re

from parser.models import Page


ITEM_PATTERN = re.compile(
    r"""
    (?im)
    ^
    \s*
    (?:
        Item
        |
        Questão
        |
        Pergunta
    )?
    \s*
    (
        (?:[1-9][0-9]?)
        (?:\.[1-9][0-9]?)?
    )
    \b
    """,
    re.VERBOSE,
)

# CORREÇÃO — bug encontrado na auditoria do banco: quando o critério de
# correção lista o gabarito de várias questões juntas (formato comum do
# IAVE em provas com cadernos duplos), o PDF imprime algo como:
#
#   Item 12. 13.
#   Versão 1 (C) (D)
#   Versão 2 (D) (B)
#
# ITEM_PATTERN (acima) só encontra UM match nesse bloco ("Item 12"),
# porque "13." está na mesma linha, não no início de uma nova — então
# todo o bloco, incluindo o gabarito da questão 13, ficava associado
# apenas à questão 12, e a questão 13 nunca recebia seu próprio
# criteria_text. Isto afetava pelo menos 7 blocos no banco atual,
# cobrindo entre 2 e 5 questões cada.
#
# ITEM_TABLE_PATTERN detecta esse formato especificamente, ANTES de
# aplicar o ITEM_PATTERN genérico, e separa o gabarito por questão,
# casando a posição de cada número com a posição correspondente em
# "Versão 1 (...)" e "Versão 2 (...)".
ITEM_TABLE_PATTERN = re.compile(
    r"""
    (?im)
    ^\s*Item\s+([\d.\s]+?)\s*\n
    \s*Vers[ãa]o\s*1\s+(.+?)\s*\n
    \s*Vers[ãa]o\s*2\s+(.+?)(?:\n|$)
    """,
    re.VERBOSE,
)

_LETTER_RE = re.compile(r"\(([A-Da-d])\)")


def _expand_item_tables(text: str) -> tuple[str, dict[str, str]]:
    """Acha blocos no formato 'Item N1. N2. ...\\nVersão 1 (...)\\nVersão 2
    (...)' e devolve (a) o texto com esses blocos removidos, para não
    confundir o ITEM_PATTERN genérico depois, e (b) um dict já pronto
    {numero: bloco_de_texto} com o gabarito correto por questão.

    Validação defensiva: se a contagem de números não bater com a
    contagem de letras em QUALQUER uma das versões, o bloco é mantido
    intacto no texto (não expandido) — é melhor cair no comportamento
    antigo (associar tudo ao primeiro número) do que arriscar uma
    associação errada por posição.
    """
    expanded: dict[str, str] = {}

    def _replace(match: re.Match) -> str:
        numbers_raw, v1_raw, v2_raw = match.group(1), match.group(2), match.group(3)
        numbers = [n.strip().rstrip(".") for n in numbers_raw.split() if n.strip(".")]
        v1_letters = _LETTER_RE.findall(v1_raw)
        v2_letters = _LETTER_RE.findall(v2_raw)

        if not numbers or len(v1_letters) != len(numbers) or len(v2_letters) != len(numbers):
            # contagem não bate — mantém o bloco original no texto,
            # para o ITEM_PATTERN genérico processar como antes
            return match.group(0)

        for number, v1, v2 in zip(numbers, v1_letters, v2_letters):
            expanded[number] = f"Versão 1 – ({v1}); Versão 2 – ({v2})"

        return ""  # remove o bloco do texto, já foi totalmente resolvido

    new_text = ITEM_TABLE_PATTERN.sub(_replace, text)
    return new_text, expanded


def parse_criteria(pages: list[Page]) -> dict[str, str]:
    text = "\n".join(page.text for page in pages)

    text, expanded_from_tables = _expand_item_tables(text)

    matches = list(ITEM_PATTERN.finditer(text))

    result: dict[str, str] = dict(expanded_from_tables)

    if not matches:
        return result

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        number = match.group(1)
        block = text[start:end].strip()

        if len(block) < 40:
            continue

        # não sobrescreve uma entrada já resolvida corretamente pela
        # expansão de tabela acima
        if number in result:
            continue

        result[number] = block

    return result
