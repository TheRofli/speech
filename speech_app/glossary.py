from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    alias: str
    canonical: str


def parse_glossary(value: str) -> list[GlossaryTerm]:
    terms: list[GlossaryTerm] = []
    seen: set[str] = set()
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "->" in line:
            alias, canonical = (part.strip() for part in line.split("->", 1))
            if not alias or not canonical:
                continue
        else:
            alias = canonical = line
        key = alias.casefold()
        if key in seen:
            continue
        seen.add(key)
        terms.append(GlossaryTerm(alias=alias, canonical=canonical))
    return terms


def apply_glossary(text: str, terms: list[GlossaryTerm]) -> str:
    result = text
    for term in sorted(terms, key=lambda item: len(item.alias), reverse=True):
        pattern = re.compile(
            rf"(?<!\w){re.escape(term.alias)}(?!\w)",
            flags=re.IGNORECASE,
        )
        result = pattern.sub(lambda _match, value=term.canonical: value, result)
    return result
