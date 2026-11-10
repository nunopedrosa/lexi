"""Text and orthography helpers for the Lexi2 corpus build.

The functions here are deliberately conservative. They produce matching keys
and automatic suggestions; they never replace the source text.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import defaultdict
from typing import Dict, Iterable, List, Sequence, Set, Tuple

WORD_RE = re.compile(
    r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['\u2019-][A-Za-zÀ-ÖØ-öø-ÿ]+)*"
)

# Consonant simplifications associated with the 1990 orthographic agreement.
# Applied only to matching keys and to explicitly flagged suggestions.
CONSONANT_RULES = (
    ("cç", "ç"),
    ("sç", "ç"),
    ("cc", "c"),
    ("pç", "ç"),
    ("mpç", "nç"),
    ("mpt", "nt"),
    ("ct", "t"),
    ("pt", "t"),
    ("pc", "c"),
    ("bt", "t"),
    ("ph", "f"),
    ("th", "t"),
    ("rh", "r"),
    ("sc", "c"),
)

OLD_PATTERN = re.compile(
    r"(cç|sç|cc|pç|mpt|ct|pt|pc|bt|ph|th|rh|sc)", re.IGNORECASE
)

VOWELS = "aeiouáéíóúâêôãõàèìòù"


def strip_accents(text: str) -> str:
    """Remove combining accents without changing the underlying letters."""

    decomposed = unicodedata.normalize("NFD", text)
    return "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )


def fold(text: str) -> str:
    """Lowercase and accent-insensitive form used for broad matching."""

    return strip_accents(text).lower()


def _apply_consonant_rules(word: str) -> Set[str]:
    current = {word}
    for old, new in CONSONANT_RULES:
        current |= {item.replace(old, new) for item in current}
    return current


def surface_keys(text: str) -> Set[str]:
    """Return safe surface variants: exact, hyphenless and prefix-assimilated.

    These keys do not apply consonant rules. They are used for automatic
    matching, so that ``mosca`` is never treated as ``moca`` and ``micto`` is
    never treated as ``mito``.
    """

    raw = text.strip().lower()
    if not raw:
        return set()

    keys: Set[str] = {raw}
    without_hyphen = raw.replace("-", "").replace(" ", "")
    keys.add(without_hyphen)

    if "-" in raw:
        parts = raw.split("-")
        if (
            len(parts) >= 2
            and parts[0]
            and parts[0][-1] in VOWELS
            and parts[1]
            and parts[1][0] in "rs"
        ):
            assimilated = parts[0] + parts[1][0] + "".join(parts[1:])
            keys.add(assimilated)

    return {key for key in keys if key}


def variant_keys(text: str) -> Set[str]:
    """Return broad candidate keys for review, not automatic attribution.

    The set includes the exact lower-case form, an accent-insensitive form,
    AO90-style consonant reductions, and the common hyphen-removal variants.
    It does not collapse arbitrary double letters, which would merge distinct
    words such as ``carro`` and ``caro``.
    """

    raw = text.strip().lower()
    if not raw:
        return set()

    keys: Set[str] = {raw, fold(raw)}

    for candidate in _apply_consonant_rules(raw):
        keys.add(candidate)
        keys.add(fold(candidate))

        without_hyphen = candidate.replace("-", "").replace(" ", "")
        keys.add(without_hyphen)
        keys.add(fold(without_hyphen))

        if "-" in candidate:
            parts = candidate.split("-")
            if (
                len(parts) >= 2
                and parts[0]
                and parts[0][-1] in VOWELS
                and parts[1]
                and parts[1][0] in "rs"
            ):
                assimilated = parts[0] + parts[1][0] + "".join(parts[1:])
                keys.add(assimilated)
                keys.add(fold(assimilated))

    return {key for key in keys if key}


def skeleton(text: str) -> str:
    """A loose grouping key used only to align the AO and pre-AO word lists."""

    raw = text.strip().lower()
    # Handle c-cedilla before NFD removes the cedilla.
    raw = raw.replace("cç", "ç").replace("sç", "ç")
    raw = fold(raw)
    for old, new in CONSONANT_RULES:
        raw = raw.replace(old, new)
    raw = raw.replace("-", "").replace(" ", "")
    return raw


def derive_preao_pairs(
    pre_only: Iterable[str], ao_only: Iterable[str]
) -> Dict[str, str]:
    """Derive pre-AO -> AO spelling pairs from the two Natura word lists.

    Alignment is based on a loose skeleton and a minimum string similarity. A
    wrong pair is a matching risk, not a silent rewrite; the caller records the
    pair and may still reject it during review.
    """

    pre_groups: Dict[str, List[str]] = defaultdict(list)
    ao_groups: Dict[str, List[str]] = defaultdict(list)

    for word in sorted(set(pre_only)):
        pre_groups[skeleton(word)].append(word)
    for word in sorted(set(ao_only)):
        ao_groups[skeleton(word)].append(word)

    pairs: Dict[str, str] = {}

    for key, pre_words in pre_groups.items():
        ao_words = ao_groups.get(key)
        if not ao_words:
            continue

        # When both sides have the same size, position pairing is normally the
        # best alignment because the source lists use the same collation.
        if len(pre_words) == len(ao_words):
            for old, new in zip(pre_words, ao_words):
                if difflib.SequenceMatcher(None, old, new).ratio() >= 0.60:
                    pairs[old] = new
            continue

        used: Set[int] = set()
        for old in pre_words:
            best_index = -1
            best_ratio = -1.0
            for index, new in enumerate(ao_words):
                if index in used:
                    continue
                ratio = difflib.SequenceMatcher(None, old, new).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_index = index
            if best_index >= 0 and best_ratio >= 0.60:
                used.add(best_index)
                pairs[old] = ao_words[best_index]

    return pairs


def tokenize(text: str) -> List[Tuple[str, int, int]]:
    """Return (token, start, end) for word-like tokens in *text*."""

    return [
        (match.group(0), match.start(), match.end())
        for match in WORD_RE.finditer(text)
    ]


def apply_case(source: str, replacement: str) -> str:
    if source.isupper() and len(source) > 1:
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement.lower()


def modernize_text(
    text: str, pre_to_ao: Dict[str, str]
) -> Tuple[str, List[Dict[str, str]], int]:
    """Replace known pre-AO tokens with their AO forms.

    Returns the suggestion, the replacements, and the number of replacements.
    The caller must keep the original text and label the result as automatic.
    """

    replacements: List[Dict[str, str]] = []

    def replace(match: re.Match) -> str:
        token = match.group(0)
        replacement = pre_to_ao.get(token.lower())
        if replacement is None:
            return token
        if replacement.lower() == token.lower():
            return token
        adjusted = apply_case(token, replacement)
        replacements.append(
            {"original": token, "replacement": adjusted}
        )
        return adjusted

    modernized = WORD_RE.sub(replace, text)
    return modernized, replacements, len(replacements)


def old_spelling_tokens(
    text: str, pre_only: Set[str], modern_words: Set[str]
) -> List[str]:
    """Return tokens that look pre-AO and are not known modern spellings."""

    found: List[str] = []
    for token, _start, _end in tokenize(text):
        lower = token.lower()
        if lower in pre_only:
            # Already recorded as a known pre-AO token by the caller.
            continue
        if lower in modern_words:
            continue
        if OLD_PATTERN.search(lower):
            found.append(token)
    return found


def split_lines(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
