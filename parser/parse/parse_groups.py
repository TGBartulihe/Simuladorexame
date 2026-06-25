from __future__ import annotations

import re

from parser.models import Group, Page
from parser.utils.question_boundaries import truncate_at_exam_end


GROUP_PATTERN = re.compile(
    r"(?im)^\s*GRUPO\s+(I|II|III|IV|V)\s*$"
)


def parse_groups(
    exam_id: int,
    pages: list[Page],
) -> list[Group]:
    full_text = "\n".join(page.text for page in pages)

    # CORREÇÃO — bug encontrado lendo o PDF original de um exame (Biologia
    # e Geologia, 2025, 1.ª fase): o IAVE imprime, depois da palavra "FIM",
    # um anexo com a tabela de cotações de toda a prova. Esse anexo ficava
    # colado ao final do ÚLTIMO grupo (normalmente o último grupo da
    # prova, ex: GRUPO III), porque nada delimitava onde o grupo "termina"
    # antes do anexo. truncate_at_exam_end() corta no marcador "FIM" (ou
    # "COTAÇÕES" como fallback) ANTES de procurar os grupos, então o
    # anexo nunca chega a fazer parte de grupo/questão nenhum.
    full_text = truncate_at_exam_end(full_text)

    matches = list(GROUP_PATTERN.finditer(full_text))

    if not matches:
        return [
            Group(
                exam_id=exam_id,
                name="SEM GRUPO",
                order=0,
                text=full_text.strip(),
            )
        ]

    groups: list[Group] = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)

        groups.append(
            Group(
                exam_id=exam_id,
                name=f"GRUPO {match.group(1)}",
                order=index,
                text=full_text[start:end].strip(),
            )
        )

    return groups
