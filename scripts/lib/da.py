"""Parsing and classification for the Dicionário Aberto SQL snapshot."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .normalize import (
    modernize_text,
    old_spelling_tokens,
    split_lines,
    tokenize,
)

WORD_ROW_RE = re.compile(
    r"\((\d+),'((?:\\.|[^'])*)',(\d+),(\d+),(\d+),'((?:\\.|[^'])*)',"
    r"(NULL|'(?:\\.|[^'])*'),'((?:\\.|[^'])*)',(NULL|\d+)\)"
)

REVISION_ROW_RE = re.compile(
    r"\((\d+),(\d+),'((?:\\.|[^'])*)','((?:\\.|[^'])*)','((?:\\.|[^'])*)',"
    r"(\d+),(NULL|'(?:\\.|[^'])*'),(NULL|'(?:\\.|[^'])*')\)"
)

BRAZIL_RE = re.compile(r"\bBras\b", re.IGNORECASE)

REGIONAL_MARKERS = (
    "Prov.",
    "trasm.",
    "minh.",
    "beir.",
    "alent.",
    "algarv.",
    "estrem.",
    "ribat.",
    "dur.",
    "sal.",
    "açor.",
    "madeir.",
    "cabo-verd.",
    "T. da",
    "T. de",
    "reg.",
    "loc.",
)

ARCHAIC_MARKERS = (
    "Ant.",
    "Des.",
    "P. us.",
    "Obs.",
    "Arcaiz.",
    "Us. ant.",
)

TECHNICAL_MARKERS = (
    "Bot.",
    "Zool.",
    "Med.",
    "Anat.",
    "Náut.",
    "Miner.",
    "Chím.",
    "Quím.",
    "Gram.",
    "Mús.",
    "Geom.",
    "Mat.",
    "Fís.",
    "Astron.",
    "Jur.",
    "Mil.",
    "Rel.",
    "Econ.",
    "Pol.",
    "Psic.",
    "Filos.",
    "Lit.",
    "Tip.",
    "Mar.",
    "Agr.",
    "Vet.",
    "Cir.",
    "Farm.",
    "Odont.",
    "Pat.",
    "Biol.",
    "Geol.",
    "Téc.",
    "Tecn.",
    "Art.",
    "Arq.",
    "Esc.",
    "Desp.",
    "Mús.",
)

POPULAR_MARKERS = ("Pop.", "Gír.", "Chul.", "Fam.", "Cal.")
POETIC_MARKERS = ("Poét.",)
NEOLOGISM_MARKERS = ("Neol.",)


def unescape_sql(value: str) -> str:
    return (
        value.replace("\\'", "'")
        .replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\\\\", "\\")
    )


def load_da(sql_path: str) -> Tuple[List[Dict], Dict[int, Dict]]:
    """Load the ``word`` table and the latest non-deleted revision per word."""

    words: List[Dict] = []
    revisions: Dict[int, Dict] = {}

    with open(sql_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "INSERT  IGNORE INTO `word`" in line:
                for match in WORD_ROW_RE.finditer(line):
                    words.append(
                        {
                            "id": int(match.group(1)),
                            "headword": unescape_sql(match.group(2)),
                            "sense": int(match.group(3)),
                            "last_revision": int(match.group(4)),
                            "deleted": int(match.group(5)),
                            "normalized": unescape_sql(match.group(8)),
                        }
                    )
            elif "INSERT  IGNORE INTO `revision`" in line:
                for match in REVISION_ROW_RE.finditer(line):
                    deleted = int(match.group(6))
                    if deleted:
                        continue
                    word_id = int(match.group(2))
                    revision_id = int(match.group(1))
                    current = revisions.get(word_id)
                    if current is None or revision_id > current["revision_id"]:
                        revisions[word_id] = {
                            "revision_id": revision_id,
                            "timestamp": unescape_sql(match.group(4)),
                            "xml": unescape_sql(match.group(5)),
                        }

    return words, revisions


def _text(element: Optional[ET.Element]) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _clean_inline(text: str) -> str:
    """Keep the source's inline markers but remove excessive whitespace."""

    return re.sub(r"[ \t]+", " ", text).strip()


def classify_label(label: str) -> Dict[str, bool]:
    """Classify a ``<usg>`` label into explicit, reviewable flags."""

    return {
        "brazil": bool(BRAZIL_RE.search(label)),
        "regional": any(marker in label for marker in REGIONAL_MARKERS),
        "archaic": any(marker in label for marker in ARCHAIC_MARKERS),
        "technical": any(marker in label for marker in TECHNICAL_MARKERS),
        "popular": any(marker in label for marker in POPULAR_MARKERS),
        "poetic": any(marker in label for marker in POETIC_MARKERS),
        "neologism": any(marker in label for marker in NEOLOGISM_MARKERS),
    }


def parse_entry_xml(xml: str) -> Dict:
    """Parse one Dicionário Aberto ``<entry>`` into a serialisable dict."""

    root = ET.fromstring(xml)
    orth = _text(root.find("form/orth")) or root.get("id", "")

    senses: List[Dict] = []
    for index, sense in enumerate(root.findall("sense"), start=1):
        usage = [
            {
                "type": element.get("type", ""),
                "text": _clean_inline(_text(element)),
            }
            for element in sense.findall("usg")
        ]
        definitions = [
            _clean_inline(_text(element))
            for element in sense.findall("def")
            if _text(element)
        ]
        definition = "\n".join(definitions)
        etymology = _text(sense.find("etym"))
        etymology_origin = ""
        etym_element = sense.find("etym")
        if etym_element is not None:
            etymology_origin = etym_element.get("orig", "")

        examples = [
            _clean_inline(_text(element))
            for element in sense.findall("example")
            if _text(element)
        ]
        cross_refs = [
            _clean_inline(_text(element))
            for element in sense.findall("xr")
            if _text(element)
        ]

        label_flags: Dict[str, bool] = {
            "brazil": False,
            "regional": False,
            "archaic": False,
            "technical": False,
            "popular": False,
            "poetic": False,
            "neologism": False,
        }
        for item in usage:
            for key, value in classify_label(item["text"]).items():
                label_flags[key] = label_flags[key] or value

        senses.append(
            {
                "index": index,
                "ast": sense.get("ast"),
                "grammar": _clean_inline(_text(sense.find("gramGrp"))),
                "usage": usage,
                "labels": [item["text"] for item in usage if item["text"]],
                "definition": definition,
                "definition_lines": split_lines(definition),
                "etymology": etymology,
                "etymology_origin": etymology_origin,
                "examples": examples,
                "cross_refs": cross_refs,
                "label_flags": label_flags,
            }
        )

    return {
        "display_headword": orth,
        "entry_type": root.get("type", ""),
        "sense_count": len(senses),
        "senses": senses,
    }


def add_review_flags(
    entry: Dict,
    pre_to_ao: Dict[str, str],
    pre_only: Set[str],
    modern_words: Set[str],
) -> None:
    """Add spelling, citation and review metadata to an entry in place."""

    for sense in entry["senses"]:
        definition = sense["definition"]
        modernized, replacements, replacement_count = modernize_text(
            definition, pre_to_ao
        )
        unresolved = old_spelling_tokens(definition, pre_only, modern_words)
        old_tokens = [
            token
            for token, _start, _end in tokenize(definition)
            if token.lower() in pre_only
        ]

        has_citation = "«" in definition or "Cf." in definition
        has_example = bool(sense["examples"]) or "_" in definition
        label_flags = sense["label_flags"]

        needs_review = bool(
            replacement_count
            or unresolved
            or label_flags["archaic"]
            or label_flags["brazil"]
            or label_flags["regional"]
        )

        sense["modernization"] = {
            "text": modernized,
            "automatic": True,
            "replacements": replacements,
            "count": replacement_count,
        }
        sense["spelling"] = {
            "old_tokens": old_tokens[:50],
            "old_token_count": len(old_tokens),
            "unresolved_old_tokens": unresolved[:50],
            "unresolved_old_token_count": len(unresolved),
            "has_old_spelling": bool(old_tokens or unresolved),
        }
        if (
            label_flags["archaic"]
            or old_tokens
            or has_citation
        ):
            review_priority = 1
        elif (
            label_flags["brazil"]
            or label_flags["regional"]
            or label_flags["technical"]
        ):
            review_priority = 2
        else:
            review_priority = 3

        sense["review"] = {
            "has_citation": has_citation,
            "has_example": has_example,
            "needs_review": needs_review,
            "priority": review_priority,
        }


def build_entries(
    words: List[Dict],
    revisions: Dict[int, Dict],
    pre_to_ao: Dict[str, str],
    pre_only: Set[str],
    modern_words: Set[str],
) -> List[Dict]:
    """Build the complete serialisable entry list."""

    entries: List[Dict] = []
    for word in words:
        if word["deleted"]:
            continue
        revision = revisions.get(word["id"])
        if revision is None:
            continue
        parsed = parse_entry_xml(revision["xml"])
        entry = {
            "id": word["id"],
            "headword": word["headword"],
            "display_headword": parsed["display_headword"],
            "normalized": word["normalized"],
            "sense_index": word["sense"],
            "entry_type": parsed["entry_type"],
            "revision_id": revision["revision_id"],
            "source_timestamp": revision["timestamp"],
            "senses": parsed["senses"],
        }
        add_review_flags(entry, pre_to_ao, pre_only, modern_words)
        entries.append(entry)
    return entries
