"""Read the words-pt plain word list."""

from __future__ import annotations

import re
from typing import Dict, List

LETTER_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")


def load_words(path: str) -> List[str]:
    """Load ``wordsList`` (ISO-8859-1, one form per line)."""

    words: List[str] = []
    with open(path, "r", encoding="iso-8859-1") as handle:
        for line in handle:
            word = line.strip()
            if word:
                words.append(word)
    return words


def classify_form(word: str) -> Dict[str, object]:
    return {
        "has_hyphen": "-" in word,
        "starts_upper": bool(word[:1].isupper()),
        "is_upper": word.isupper() and len(word) > 1,
        "has_letter": bool(LETTER_RE.search(word)),
    }


def basic_stats(words: List[str]) -> Dict[str, int]:
    return {
        "total": len(words),
        "unique": len(set(words)),
        "hyphenated": sum("-" in word for word in words),
        "non_hyphenated": sum("-" not in word for word in words),
        "starts_upper": sum(bool(word[:1].isupper()) for word in words),
        "siglas": sum(word.isupper() and len(word) > 1 for word in words),
        "words_without_letters": sum(
            not bool(LETTER_RE.search(word)) for word in words
        ),
    }
