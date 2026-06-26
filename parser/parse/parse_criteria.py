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
    \.
    (?!\d)
    """,
    re.VERBOSE,
)
# CORREÇÃO — bug encontrado testando contra o PDF real: o padrão original
# não exigia um "." logo após o número, só um \b (word boundary). Isso
# fazia a linha "8 pontos" (a cotação da questão anterior, impressa numa
# linha própria por causa dos pontos de preenchimento do PDF) ser lida
# como se fosse "questão número 8" — criando uma entrada de critério
# espúria que continha, na verdade, o conteúdo da questão seguinte
# (efeito cascata: todos os blocos depois ficavam deslocados em um).
# Exigir um "." literal após o número (e não seguido de outro dígito,
# para não cortar "15.1" no meio) resolve isso: "8 pontos" não tem ponto
# depois do número, "8." (de uma questão real) tem.

# CORREÇÃO — bug encontrado na auditoria do banco: quando o critério de
# correção lista o gabarito de várias questões juntas (formato comum do
# IAVE em provas com cadernos duplos), o PDF imprime uma tabela assim:
#
#   Item 12. 13.
#   Versão 1 (C) (D)
#   Versão 2 (D) (B)
#
# ITEM_PATTERN (acima) só encontra UM match nesse bloco ("Item 12"),
# porque "13." está na mesma linha lógica, não no início de uma nova —
# então todo o bloco, incluindo o gabarito da questão 13, ficava
# associado apenas à questão 12, e a questão 13 nunca recebia seu
# próprio criteria_text. Isto afetava pelo menos 7 blocos no banco
# atual, cobrindo entre 2 e 5 questões cada.
#
# CORREÇÃO DA CORREÇÃO (achado testando contra o PDF real, não só uma
# reconstrução manual): a extração real do PDF não produz "Item 12. 13."
# numa única linha como eu tinha assumido inicialmente. Ela produz CADA
# token em sua própria linha:
#
#   Item
#   12.
#   13.
#   Versão 1
#   (C)
#   (D)
#   Versão 2
#   (D)
#   (B)
#
# Um regex single-line (como a primeira versão desta correção usava)
# nunca casa com esse formato. _parse_item_tables() abaixo lê o texto
# linha por linha em vez de tentar capturar tudo com um único regex —
# mais verboso, mas reflete a estrutura real extraída do PDF.
_ITEM_LINE_RE = re.compile(r"^\d+(?:\.\d+)?\.$")
_VERSAO_1_LINE_RE = re.compile(r"(?i)^vers[ãa]o\s*1\s*$")
_VERSAO_2_LINE_RE = re.compile(r"(?i)^vers[ãa]o\s*2\s*$")
_LETTER_LINE_RE = re.compile(r"^\(([A-Da-d])\)$")

_LETTER_RE = re.compile(r"\(([A-Da-d])\)")


def _parse_item_tables(text: str) -> tuple[str, dict[str, str]]:
    """Acha blocos no formato (linha por linha):
        Item
        N1.
        N2.
        ...
        Versão 1
        (L1)
        (L2)
        ...
        Versão 2
        (L1)
        (L2)
        ...
    e devolve (a) o texto com essas linhas removidas, para não confundir
    o ITEM_PATTERN genérico depois, e (b) um dict já pronto
    {numero: texto_do_gabarito} com o gabarito correto por questão.

    Validação defensiva: se a contagem de números não bater com a
    contagem de letras em QUALQUER uma das versões, o bloco é mantido
    intacto no texto (não expandido) — é melhor cair no comportamento
    antigo (associar tudo ao primeiro número) do que arriscar uma
    associação errada por posição.
    """
    lines = text.splitlines()
    expanded: dict[str, str] = {}
    output_lines: list[str] = []

    i = 0
    while i < len(lines):
        if lines[i].strip().lower() != "item":
            output_lines.append(lines[i])
            i += 1
            continue

        # possível início de tabela — tenta consumir o padrão completo
        # sem alterar `output_lines` ainda (só confirma e aplica se a
        # validação no final passar)
        j = i + 1
        numbers: list[str] | None = []
        while j < len(lines) and not _VERSAO_1_LINE_RE.match(lines[j].strip()):
            stripped = lines[j].strip()
            if _ITEM_LINE_RE.match(stripped):
                numbers.append(stripped.rstrip("."))
            elif stripped:
                numbers = None  # linha inesperada — não é uma tabela válida
                break
            j += 1

        if not numbers or j >= len(lines):
            output_lines.append(lines[i])
            i += 1
            continue

        j += 1  # pula a linha "Versão 1"
        v1_letters: list[str] = []
        while j < len(lines) and len(v1_letters) < len(numbers):
            stripped = lines[j].strip()
            m = _LETTER_LINE_RE.match(stripped)
            if m:
                v1_letters.append(m.group(1).upper())
            elif stripped:
                break
            j += 1

        if j >= len(lines) or not _VERSAO_2_LINE_RE.match(lines[j].strip()):
            output_lines.append(lines[i])
            i += 1
            continue

        j += 1  # pula a linha "Versão 2"
        v2_letters: list[str] = []
        while j < len(lines) and len(v2_letters) < len(numbers):
            stripped = lines[j].strip()
            m = _LETTER_LINE_RE.match(stripped)
            if m:
                v2_letters.append(m.group(1).upper())
            elif stripped:
                break
            j += 1

        if len(numbers) == len(v1_letters) == len(v2_letters):
            for number, v1, v2 in zip(numbers, v1_letters, v2_letters):
                expanded[number] = f"Versão 1 – ({v1}); Versão 2 – ({v2})"
            i = j  # consome todas as linhas da tabela, não as copia para output_lines
        else:
            # contagem não bateu — mantém a linha "Item" original e
            # deixa o ITEM_PATTERN genérico tentar processar como antes
            output_lines.append(lines[i])
            i += 1

    return "\n".join(output_lines), expanded


def parse_criteria(pages: list[Page]) -> dict[str, str]:
    text = "\n".join(page.text for page in pages)

    text, expanded_from_tables = _parse_item_tables(text)

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
