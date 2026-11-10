"""Wiktionary bridge layer (sibling Lexi snapshot).

The snapshot is the dictionary data compiled in the sibling Lexi project from
the Portuguese and English Wiktionaries via kaikki.org (wiktextract). It is
pinned per file by ``scripts/fetch_sources.py`` and lives in
``.work/sources/lexi-wikt/``.

Everything imported from it is a CC BY-SA 4.0 third-party layer. Senses are
flagged ``wikt`` in the runtime data and are never merged into, or presented
as, Dicionário Aberto or reviewed content. Brazilian-labelled senses keep the
source's own labels: the explicit ``BR`` mark is preserved, and a conservative
parenthetical-label scan (``(Brazil``, ``(Brasil``) marks additional senses.

The snapshot stores each sense as ``[text, mark, flags]`` and, for senses
touched by Lexi's unrevised automatic PT-PT adaptation, a fourth element
``{"original": ..., "rules": [...]}``. The original text is restored and the
adapted wording becomes a separately flagged suggestion, mirroring the
Dicionário Aberto modernization model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SNAPSHOT_DIR = "lexi-wikt"
FILE_ORDER = ["_"] + [chr(code) for code in range(ord("a"), ord("z") + 1)]

# Parenthetical Brazilian labels that appear inside the definition text.
BRAZIL_MARKERS = ("(Brazil", "(Brasil")

# Lexi part-of-speech labels mapped to the Lexi2 presentation style. Unknown
# values are dropped rather than guessed.
POS_MAP = {
    "n.": "n.",
    "adj.": "adj.",
    "v.": "v.",
    "adv.": "adv.",
    "phr.": "loc.",
    "interj.": "interj.",
    "pron.": "pron.",
    "conj.": "conj.",
    "num.": "num.",
    "prep.": "prep.",
    "pref.": "pref.",
    "suf.": "suf.",
    "det.": "det.",
}


def snapshot_dir(sources_dir: Path) -> Path:
    return Path(sources_dir) / SNAPSHOT_DIR


def load_entries(sources_dir: Path) -> Dict[str, Dict]:
    """Load the snapshot in a fixed file order; the first occurrence wins.

    Entries are indexed by their exact headword. Matching is therefore
    case-sensitive: a lowercase Hunspell lemma never matches a capitalised
    headword, which keeps proper nouns out of the bridge.
    """

    base = snapshot_dir(sources_dir)
    entries: Dict[str, Dict] = {}
    for key in FILE_ORDER:
        path = base / ("%s.json" % key)
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as handle:
            records = json.load(handle)
        for record in records:
            if not isinstance(record, list) or not record:
                continue
            headword = record[0]
            if not isinstance(headword, str) or not headword:
                continue
            if headword in entries:
                continue
            entries[headword] = {
                "headword": headword,
                "pos": record[1] if len(record) > 1 else "",
                "senses": record[2] if len(record) > 2 else [],
            }
    return entries


def match_entry(
    lemma: str,
    preao90: Optional[str],
    entries: Dict[str, Dict],
) -> Optional[Tuple[str, Dict]]:
    """Match a missing lemma against the snapshot.

    ``exact`` is a case-sensitive headword match on the modern lemma.
    ``preao90`` matches the recorded pre-AO spelling; the row is still
    presented under the modern lemma and flagged ``old``.
    """

    direct = entries.get(lemma)
    if direct:
        return "exact", direct
    if preao90:
        old = entries.get(preao90)
        if old:
            return "preao90", old
    return None


def convert_pos(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    return POS_MAP.get(raw.strip(), "")


def convert_senses(entry: Dict, matched_preao: bool) -> List[List]:
    """Convert snapshot senses into Lexi2 sense rows.

    Returns ``[text, region, flags, modernized, source]`` rows with
    ``wikt`` always flagged, Brazilian senses last, and duplicates removed
    while preserving the source order.
    """

    converted: List[List] = []
    for sense in entry.get("senses") or []:
        if not isinstance(sense, list) or not sense:
            continue
        text = sense[0] if isinstance(sense[0], str) else ""
        text = " ".join(text.split())
        if not text:
            continue

        flags = ["wikt"]
        modernized = ""
        # Lexi's unrevised automatic PT-PT adaptation keeps the original
        # wording in a fourth element. Restore it; offer the adapted text as
        # a flagged suggestion only.
        if len(sense) > 3 and isinstance(sense[3], dict):
            original = sense[3].get("original")
            if isinstance(original, str):
                original = " ".join(original.split())
                if original:
                    adapted = text
                    text = original
                    if adapted != original:
                        modernized = adapted
                        flags.append("mod")

        mark = sense[1] if len(sense) > 1 and isinstance(sense[1], str) else ""
        region = "BR" if mark.strip().upper() == "BR" else ""
        if not region and any(marker in text for marker in BRAZIL_MARKERS):
            region = "BR"
        if matched_preao:
            flags.append("old")

        converted.append([text, region, flags, modernized, entry["headword"]])

    unique: List[List] = []
    seen = set()
    for row in converted:
        key = (row[0], row[1], tuple(row[2]), row[3])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    # Stable sort: PT-PT/unmarked senses keep the source order and come
    # first; senses labelled Brazilian are grouped last.
    unique.sort(key=lambda row: row[1] == "BR")
    return unique


def build_row(lemma: str, match_type: str, entry: Dict) -> Optional[Dict]:
    """Build a Lexi2 dictionary row for a bridged lemma."""

    senses = convert_senses(entry, match_type == "preao90")
    if not senses:
        return None
    br_all = all(row[1] == "BR" for row in senses)
    return {
        "headword": lemma,
        "pos": convert_pos(entry.get("pos")),
        "senses": senses,
        "status": "br" if br_all else "ok",
    }
