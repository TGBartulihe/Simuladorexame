from __future__ import annotations

import re


PAGE_PATTERN = re.compile(
    r"--- PAGE\s+\d+\s+---",
    re.IGNORECASE,
)

HEADER_PATTERNS = [
    r"Prova\s+\d+.*?Página\s+\d+\s*/\s*\d+",
    r"IAVE.*",
    r"INSTITUTO.*",
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