"""Read the Hunspell pt_PT dictionary without a Hunspell runtime."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

ATTR_RE = re.compile(r"(?:^|,)([A-Z0-9_]+)=([^,]*)")
LEMMA_LINK_RE = re.compile(r"\$([^$]+)\$")
PREAO90_RE = re.compile(r"PREAO90=([^,\]]+)")
CAT_RE = re.compile(r"CAT=([^,\]]+)")


def parse_dic(path: str) -> Dict:
    """Parse ``pt_PT.dic`` into base lemmas, explicit forms and metadata.

    The dictionary's explicit forms use ``[$lemma$...]`` links. The base
    entries are lemmas, including proper nouns and siglas; those are separated
    so the missing-lemma list can exclude them without losing the diagnostic.
    """

    base: List[Dict] = []
    forms: List[Dict] = []
    preao90: Dict[str, str] = {}
    proper_nouns: List[str] = []
    siglas: List[str] = []
    punctuation: List[str] = []

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        first = True
        for line in handle:
            if first:
                first = False
                line = line.lstrip("\ufeff")
                if line.strip().isdigit():
                    continue
            if not line.strip():
                continue

            head, _, attributes = line.partition("\t")
            word_part = head.strip()
            if not word_part:
                continue
            word = word_part.split("/", 1)[0].strip()
            if not word:
                continue

            cats = set(CAT_RE.findall(attributes))
            pre = PREAO90_RE.search(attributes)
            pre_value = pre.group(1).strip() if pre else None
            if pre_value:
                preao90[word] = pre_value

            link = LEMMA_LINK_RE.search(attributes)
            if link:
                forms.append(
                    {
                        "form": word,
                        "lemma": link.group(1),
                        "categories": sorted(cats),
                        "attributes": attributes,
                    }
                )
                continue

            record = {
                "word": word,
                "categories": sorted(cats),
                "preao90": pre_value,
                "attributes": attributes,
            }
            base.append(record)

            if not any(char.isalpha() for char in word):
                punctuation.append(word)
            elif "np" in cats:
                proper_nouns.append(word)
            elif word.isupper() and len(word) > 1:
                siglas.append(word)

    return {
        "base": base,
        "forms": forms,
        "preao90": preao90,
        "proper_nouns": proper_nouns,
        "siglas": siglas,
        "punctuation": punctuation,
    }


def is_lexical_lemma(record: Dict) -> bool:
    """Whether a base entry belongs in the default lemma universe."""

    word = record["word"]
    cats = set(record["categories"])

    if not any(char.isalpha() for char in word):
        return False
    if "np" in cats:
        return False
    if any(category.startswith("punct") for category in cats):
        return False
    if "pref" in cats:
        return False
    if word.isupper() and len(word) > 1:
        return False
    if len(word) > 1 and len(set(word.lower())) == 1:
        return False
    return True


def build_form_index(forms: Iterable[Dict]) -> Dict[str, Set[str]]:
    index: Dict[str, Set[str]] = defaultdict(set)
    for record in forms:
        index[record["form"]].add(record["lemma"])
    return dict(index)
