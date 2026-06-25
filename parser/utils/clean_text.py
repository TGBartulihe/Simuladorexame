from __future__ import annotations

import re


PAGE_PATTERN = re.compile(
    r"--- PAGE\s+\d+\s+---",
    re.IGNORECASE,
)

# CORREÇÃO — bug encontrado lendo o PDF original de um exame (Biologia e
# Geologia, 2025, 1.ª fase): o padrão "IAVE.*" e "INSTITUTO.*", sem
# ancoragem ao início da linha, removiam QUALQUER linha que contivesse
# essas palavras em qualquer posição — não só o timbre institucional do
# cabeçalho ("IAVE — INSTITUTO DE AVALIAÇÃO EDUCATIVA, I.P."), mas também
# enunciados legítimos que mencionam outras instituições de passagem.
# Caso real: a questão "4." do GRUPO III começava com "De acordo com o
# Instituto Português do Mar e da Atmosfera (IPMA)..." — a palavra
# "Instituto" ali é um substantivo comum dentro do enunciado, não o
# timbre da prova, mas o padrão antigo a removia inteira, fazendo a
# questão 4 inteira desaparecer silenciosamente (a linha com o "4."
# inicial era exatamente a removida, então a questão nem era detectada
# como existente pelo parser de questões mais adiante no pipeline).
#
# A correção ancora cada padrão ao INÍCIO da linha (^\s*) e usa o texto
# específico do timbre real do IAVE, em vez de uma palavra genérica que
# pode aparecer em qualquer enunciado.
HEADER_PATTERNS = [
    r"^\s*Prova\s+\d+.*?Página\s+\d+\s*/\s*\d+",
    r"^\s*IAVE(?:\s|$)",
    r"^\s*INSTITUTO\s+DE\s+AVALIA[ÇC][ÃA]O\s+EDUCATIVA",
]

HEADER_REGEX = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in HEADER_PATTERNS
]

MULTISPACE = re.compile(r"[ \t]{2,}")
MULTIBREAK = re.compile(r"\n{3,}")
SOFT_HYPHEN = "\u00ad"


def normalize_unicode(text: str) -> str:
    text = text.replace(SOFT_HYPHEN, "")
    text = text.replace("\ufeff", "")
    return text


def remove_headers(text: str) -> str:
    lines = []

    for line in text.splitlines():
        skip = False

        for regex in HEADER_REGEX:
            if regex.search(line):
                skip = True
                break

        if not skip:
            lines.append(line)

    return "\n".join(lines)


def normalize_spaces(text: str) -> str:
    text = MULTISPACE.sub(" ", text)
    text = MULTIBREAK.sub("\n\n", text)
    return text.strip()


def remove_page_markers(text: str) -> str:
    return PAGE_PATTERN.sub("", text)


def clean_text(text: str) -> str:
    text = normalize_unicode(text)
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = remove_page_markers(text)
    text = remove_headers(text)
    text = normalize_spaces(text)
    return text
