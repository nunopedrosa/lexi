#!/usr/bin/env python3
"""Build the Lexi2 lemma-first corpus and its missing-lemma report.

The pipeline is intentionally reproducible:

1. verify the pinned source snapshots;
2. parse the Dicionário Aberto entries and senses;
3. derive conservative pre-AO -> AO spelling pairs;
4. parse the Hunspell lemma/form metadata;
5. match the modern lemma universe against Dicionário Aberto;
6. write the lemma-only missing list, the audit and the report.

It does not publish, deploy or modify the sibling Lexi project.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_sources import (  # noqa: E402
    DEFAULT_BUILD,
    DEFAULT_SOURCES,
    find_hunspell,
    verify_sources,
)
from lib.da import build_entries, load_da  # noqa: E402
from lib.forms import build_stem_index, hunspell_available  # noqa: E402
from lib.hunspell import build_form_index, is_lexical_lemma, parse_dic  # noqa: E402
from lib.normalize import (  # noqa: E402
    derive_preao_pairs,
    fold,
    surface_keys,
    variant_keys,
)
from lib.wordspt import basic_stats, load_words  # noqa: E402
from lib.wikt import (  # noqa: E402
    build_row as wikt_build_row,
    load_entries as load_wikt_entries,
    match_entry as match_wikt_entry,
)

PRONOUNS = {
    "me",
    "te",
    "se",
    "lhe",
    "lhes",
    "nos",
    "vos",
    "o",
    "a",
    "os",
    "as",
    "no",
    "na",
    "los",
    "las",
    "lo",
    "la",
    "mo",
    "ma",
    "mos",
    "mas",
    "to",
    "ta",
    "tos",
    "tas",
    "lho",
    "lha",
    "lhos",
    "lhas",
    "nho",
    "nha",
    "nhos",
    "nhas",
}


def load_plain_list(path: Path) -> List[str]:
    with open(path, "r", encoding="iso-8859-1") as handle:
        return [line.strip() for line in handle if line.strip()]


def load_preao_supplement(path: Path) -> Dict[str, str]:
    """Load reviewed ``pre-AO|modern`` spelling pairs."""

    pairs: Dict[str, str] = {}
    if not path.exists():
        return pairs
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                continue
            old, new = parts[0].lower(), parts[1].lower()
            if old != new:
                pairs[old] = new
    return pairs


def load_curated_definitions(path: Path) -> List[Dict]:
    """Load approved ``lemma|pos|definition`` editorial entries."""

    records: List[Dict] = []
    if not path.exists():
        return records
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 3 or not parts[0]:
                continue
            # Optional region field (4 segments): lemma|pos|region|definition.
            # Existing 3-segment rows stay unmarked. Region values follow the
            # Dicionário Aberto convention (e.g. "BR" for Brazilian senses).
            if len(parts) >= 4:
                region = parts[2].upper()
                definition = parts[3]
            else:
                region = ""
                definition = parts[2]
            if not definition:
                continue
            records.append(
                {
                    "lemma": parts[0],
                    "pos": parts[1],
                    "region": region,
                    "definition": definition,
                }
            )
    return records


def load_curated_lemmas(path: Path) -> List[Dict]:
    """Load ``lemma|pos|note`` lines from the curated supplement."""

    records: List[Dict] = []
    if not path.exists():
        return records
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split("|")]
            lemma = parts[0] if parts else ""
            if not lemma:
                continue
            records.append(
                {
                    "lemma": lemma,
                    "pos": parts[1] if len(parts) > 1 else "",
                    "note": parts[2] if len(parts) > 2 else "",
                }
            )
    return records


def lower_set(values: Iterable[str]) -> Set[str]:
    return {value.lower() for value in values}


def make_preao_map(
    pre_words: List[str],
    ao_words: List[str],
    hunspell_data: Dict,
    supplement: Dict[str, str],
) -> Tuple[Dict[str, str], Set[str], Set[str], Dict[str, int]]:
    """Combine the Natura alignment with authoritative Hunspell PREAO90 data."""

    pre_set = lower_set(pre_words)
    ao_set = lower_set(ao_words)
    pre_only = pre_set - ao_set
    ao_only = ao_set - pre_set

    derived = derive_preao_pairs(pre_only, ao_only)
    pre_to_ao: Dict[str, str] = {
        old.lower(): new.lower()
        for old, new in derived.items()
        if old.lower() != new.lower()
    }

    authoritative = 0
    for modern, old in hunspell_data["preao90"].items():
        modern_lower = modern.lower()
        old_lower = old.lower()
        if modern_lower == old_lower:
            # Case-only variants (for example April/Abril) are not spelling
            # changes and must not be used for matching.
            continue
        pre_to_ao[old_lower] = modern_lower
        authoritative += 1

    # Reviewed supplement pairs take precedence over automatic alignment.
    pre_to_ao.update(supplement)

    # A pre-AO token is only "old" when it is not also a valid modern word.
    pre_only_set = set(pre_to_ao) - ao_set
    modern_words = ao_set | set(pre_to_ao.values())

    stats = {
        "derived_pairs": len(derived),
        "authoritative_preao90_pairs": authoritative,
        "supplement_pairs": len(supplement),
        "pre_only_tokens": len(pre_only_set),
        "modern_words": len(modern_words),
        "pre_to_ao_pairs": len(pre_to_ao),
    }
    return pre_to_ao, pre_only_set, modern_words, stats


def build_indexes(
    entries: List[Dict],
    supplement: Dict[str, str],
) -> Dict[str, Dict]:
    """Build exact, accent, surface and review-candidate indexes.

    ``surface`` is deliberately limited to hyphen and spacing variants.
    ``candidates`` uses the broader consonant rules but is only consulted to
    suggest a near match for a missing lemma; it never attributes a definition
    automatically. ``reviewed_modern_to_pre`` contains only the reviewed
    pre-AO supplement pairs, so they can resolve a modern lemma safely.
    """

    exact: Dict[str, int] = {}
    folded: Dict[str, int] = {}
    surface: Dict[str, int] = {}
    candidates: Dict[str, int] = {}
    reviewed_modern_to_pre: Dict[str, List[str]] = {}

    for pre, modern in supplement.items():
        reviewed_modern_to_pre.setdefault(modern, []).append(pre)

    for entry in entries:
        headword = entry["headword"]
        lower = headword.lower()
        exact.setdefault(lower, entry["id"])
        folded.setdefault(fold(headword), entry["id"])
        for key in surface_keys(headword):
            surface.setdefault(key, entry["id"])
        for key in variant_keys(headword):
            candidates.setdefault(key, entry["id"])

    return {
        "exact": exact,
        "folded": folded,
        "surface": surface,
        "candidates": candidates,
        "reviewed_modern_to_pre": reviewed_modern_to_pre,
    }


def match_lemma(
    lemma: str,
    preao90: Optional[str],
    indexes: Dict[str, Dict[str, int]],
    entries_by_id: Dict[int, Dict],
) -> Optional[Dict]:
    lower = lemma.lower()

    if lower in indexes["exact"]:
        entry_id = indexes["exact"][lower]
        return {
            "type": "exact",
            "entry_id": entry_id,
            "headword": entries_by_id[entry_id]["headword"],
        }

    if preao90:
        pre_lower = preao90.lower()
        if pre_lower in indexes["exact"]:
            entry_id = indexes["exact"][pre_lower]
            return {
                "type": "preao90",
                "entry_id": entry_id,
                "headword": entries_by_id[entry_id]["headword"],
            }

    for pre in indexes.get("reviewed_modern_to_pre", {}).get(lower, []):
        if pre in indexes["exact"]:
            entry_id = indexes["exact"][pre]
            return {
                "type": "supplement",
                "entry_id": entry_id,
                "headword": entries_by_id[entry_id]["headword"],
            }

    if lower in indexes["surface"]:
        entry_id = indexes["surface"][lower]
        headword = entries_by_id[entry_id]["headword"]
        if headword.lower() != lower:
            return {
                "type": "orthographic",
                "entry_id": entry_id,
                "headword": headword,
            }

    folded = fold(lemma)
    if folded in indexes["folded"]:
        entry_id = indexes["folded"][folded]
        return {
            "type": "accent",
            "entry_id": entry_id,
            "headword": entries_by_id[entry_id]["headword"],
        }

    return None


def find_candidate(
    lemma: str,
    indexes: Dict[str, Dict[str, int]],
    entries_by_id: Dict[int, Dict],
) -> Optional[Dict]:
    """Find a near DA headword for review, without attributing it."""

    lower = lemma.lower()
    for key in variant_keys(lemma):
        if key in indexes["candidates"]:
            entry_id = indexes["candidates"][key]
            headword = entries_by_id[entry_id]["headword"]
            if headword.lower() == lower:
                continue
            return {
                "type": "candidate",
                "entry_id": entry_id,
                "headword": headword,
            }
    return None


def build_lemmas(
    hunspell_data: Dict,
    words_lower: Set[str],
    ao_set: Set[str],
    pre_set: Set[str],
    indexes: Dict[str, Dict[str, int]],
    entries_by_id: Dict[int, Dict],
    curated_lemmas: List[Dict],
    curated_definitions: List[Dict],
) -> List[Dict]:
    """Build the modern lemma universe and its DA match status."""

    def add_source(existing: str, new: str) -> str:
        parts = set(existing.split("+")) | {new}
        return "+".join(sorted(parts))

    by_lower: Dict[str, Dict] = {}

    for record in hunspell_data["base"]:
        if not is_lexical_lemma(record):
            continue
        lemma = record["word"]
        key = lemma.lower()
        categories = set(record["categories"])
        if key in by_lower:
            by_lower[key]["pos"] = sorted(
                set(by_lower[key]["pos"]) | categories
            )
            continue

        by_lower[key] = {
            "lemma": lemma,
            "lower": key,
            "pos": sorted(categories),
            "preao90": record["preao90"],
            "in_words_pt": key in words_lower,
            "in_ao_list": key in ao_set,
            "in_preao_list": key in pre_set,
            "preao90_in_preao_list": bool(
                record["preao90"]
                and record["preao90"].lower() in pre_set
            ),
            "source": "hunspell",
        }

    for curated in curated_lemmas:
        lemma = curated["lemma"]
        key = lemma.lower()
        if key in by_lower:
            by_lower[key]["source"] = add_source(
                by_lower[key]["source"], "curated"
            )
            if curated["note"]:
                by_lower[key]["curated_note"] = curated["note"]
            if curated["pos"]:
                by_lower[key]["pos"] = sorted(
                    set(by_lower[key]["pos"]) | {curated["pos"]}
                )
            continue
        by_lower[key] = {
            "lemma": lemma,
            "lower": key,
            "pos": [curated["pos"]] if curated["pos"] else [],
            "preao90": None,
            "in_words_pt": key in words_lower,
            "in_ao_list": key in ao_set,
            "in_preao_list": key in pre_set,
            "preao90_in_preao_list": False,
            "source": "curated",
            "curated_note": curated["note"],
        }

    lemmas: List[Dict] = []
    for key in sorted(by_lower):
        record = by_lower[key]
        match = match_lemma(
            record["lemma"],
            record["preao90"],
            indexes,
            entries_by_id,
        )
        if match:
            record["status"] = "matched"
            record["match"] = match
            record["near_da"] = None
            record["notes"] = ""
        else:
            record["status"] = "missing"
            record["match"] = None
            record["near_da"] = find_candidate(
                record["lemma"], indexes, entries_by_id
            )
            notes = ["no_da_entry"]
            if record["near_da"]:
                notes.append("near_da_candidate")
            if "curated" in record["source"].split("+"):
                notes.append("curated_supplement")
            if not record["in_words_pt"]:
                notes.append("not_in_words_pt")
            if record["preao90"] and record["preao90"].lower() not in pre_set:
                notes.append("preao90_not_in_natura_list")
            record["notes"] = ";".join(notes)
            if "curated" in record["source"].split("+"):
                record["priority"] = 1
            elif record["near_da"] or record["preao90"]:
                record["priority"] = 1
            elif record["in_ao_list"]:
                record["priority"] = 2
            else:
                record["priority"] = 3
        lemmas.append(record)

    by_lower_map = {record["lower"]: record for record in lemmas}
    for item in curated_definitions:
        record = by_lower_map.get(item["lemma"].lower())
        if not record or record["status"] == "matched":
            continue
        record["status"] = "editorial"
        record["match"] = {
            "type": "editorial",
            "entry_id": None,
            "headword": record["lemma"],
        }
        record["notes"] = "curated_definition"
        record["priority"] = 0
        record["editorial_definition"] = item["definition"]
        record["editorial_pos"] = item["pos"]
        record["editorial_region"] = item.get("region", "")

    return lemmas


def collect_flag_counts(entries: List[Dict]) -> Dict[str, object]:
    label_keys = (
        "brazil",
        "regional",
        "archaic",
        "technical",
        "popular",
        "poetic",
        "neologism",
    )
    senses_by_label = {key: 0 for key in label_keys}
    entries_by_label = {key: set() for key in label_keys}
    old_spelling_senses = 0
    modernized_senses = 0
    modernization_replacements = 0
    review_senses = 0
    citation_senses = 0
    example_senses = 0
    review_priority = Counter()

    for entry in entries:
        for sense in entry["senses"]:
            review_priority[sense["review"].get("priority", 3)] += 1
            labels = sense["label_flags"]
            for key in label_keys:
                if labels[key]:
                    senses_by_label[key] += 1
                    entries_by_label[key].add(entry["id"])
            if sense["spelling"]["has_old_spelling"]:
                old_spelling_senses += 1
            if sense["modernization"]["count"]:
                modernized_senses += 1
                modernization_replacements += sense["modernization"]["count"]
            if sense["review"]["needs_review"]:
                review_senses += 1
            if sense["review"]["has_citation"]:
                citation_senses += 1
            if sense["review"]["has_example"]:
                example_senses += 1

    return {
        "senses_by_label": senses_by_label,
        "entries_by_label": {
            key: len(value) for key, value in entries_by_label.items()
        },
        "old_spelling_senses": old_spelling_senses,
        "modernized_senses": modernized_senses,
        "modernization_replacements": modernization_replacements,
        "needs_review_senses": review_senses,
        "citation_senses": citation_senses,
        "example_senses": example_senses,
        "review_priority": {
            str(key): value for key, value in sorted(review_priority.items())
        },
    }


def resolve_hyphenated(word: str, known: Set[str]) -> Tuple[bool, Optional[str]]:
    """Try to resolve an enclitic form by removing one or two pronouns."""

    parts = word.split("-")
    if len(parts) < 2:
        return False, None

    for count in (1, 2):
        if len(parts) <= count:
            continue
        tail = parts[-count:]
        if not all(part.lower() in PRONOUNS for part in tail):
            continue
        base = "-".join(parts[:-count]).lower()
        if base in known:
            return True, base
    return False, None


def words_coverage(
    words: List[str],
    indexes: Dict[str, Dict[str, int]],
    hunspell_forms: Dict[str, Set[str]],
    hunspell_base_lemmas: Set[str],
    hunspell_lemma_status: Dict[str, str],
) -> Dict[str, int]:
    exact = 0
    orthographic = 0
    accent = 0
    candidate = 0
    hunspell_form = 0
    hunspell_form_resolved = 0
    hunspell_base = 0
    hunspell_base_resolved = 0
    hyphenated = 0
    hyphenated_resolved = 0
    unresolved = 0

    exact_keys = indexes["exact"]
    surface_keys_set = indexes["surface"]
    folded_keys = indexes["folded"]
    candidate_keys = indexes["candidates"]

    known_for_hyphen = set(exact_keys) | set(surface_keys_set)

    for word in words:
        lower = word.lower()
        matched = False

        if lower in exact_keys:
            exact += 1
            matched = True
        elif lower in surface_keys_set:
            orthographic += 1
            matched = True
        elif fold(lower) in folded_keys:
            accent += 1
            matched = True
        elif lower in candidate_keys:
            candidate += 1

        if lower in hunspell_forms:
            hunspell_form += 1
            if any(
                hunspell_lemma_status.get(lemma.lower()) in ("matched", "editorial")
                for lemma in hunspell_forms[lower]
            ):
                hunspell_form_resolved += 1
            matched = True

        if lower in hunspell_base_lemmas:
            hunspell_base += 1
            if hunspell_lemma_status.get(lower) in ("matched", "editorial"):
                hunspell_base_resolved += 1
            matched = True

        if "-" in word:
            hyphenated += 1
            resolved, _base = resolve_hyphenated(word, known_for_hyphen)
            if resolved:
                hyphenated_resolved += 1
                matched = True

        if not matched:
            unresolved += 1

    return {
        "exact_da_headword": exact,
        "orthographic_da_match": orthographic,
        "accent_da_match": accent,
        "review_candidate_only": candidate,
        "explicit_hunspell_form": hunspell_form,
        "explicit_hunspell_form_with_da_lemma": hunspell_form_resolved,
        "hunspell_base_lemma": hunspell_base,
        "hunspell_base_lemma_with_da_lemma": hunspell_base_resolved,
        "hyphenated": hyphenated,
        "hyphenated_resolved": hyphenated_resolved,
        "unresolved": unresolved,
    }


def write_jsonl(path: Path, records: Iterable[Dict]) -> int:
    count = 0
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_missing_files(
    docs_dir: Path,
    missing: List[Dict],
) -> None:
    csv_path = docs_dir / "missing-lemmas.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "priority",
                "lemma",
                "source",
                "pos",
                "preao90",
                "lemma_in_words_pt",
                "lemma_in_ao_list",
                "preao90_in_preao_list",
                "near_da_headword",
                "near_da_entry_id",
                "curated_note",
                "wikt_headword",
                "notes",
            ]
        )
        for record in missing:
            near = record.get("near_da") or {}
            writer.writerow(
                [
                    record.get("priority", 3),
                    record["lemma"],
                    record["source"],
                    "|".join(record["pos"]),
                    record["preao90"] or "",
                    "yes" if record["in_words_pt"] else "no",
                    "yes" if record["in_ao_list"] else "no",
                    "yes" if record["preao90_in_preao_list"] else "no",
                    near.get("headword", ""),
                    near.get("entry_id", ""),
                    record.get("curated_note", ""),
                    (record.get("wikt") or {}).get("headword", ""),
                    record["notes"],
                ]
            )

    (docs_dir / "missing-lemmas.json").write_text(
        json.dumps(missing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def form_index_stats(
    form_index: Dict[str, List[str]],
    words: List[str],
    lemma_status: Dict[str, str],
) -> Dict[str, int]:
    matched_forms = 0
    missing_only_forms = 0
    ambiguous_forms = 0
    hyphenated_forms = 0

    for form, stems in form_index.items():
        statuses = [lemma_status.get(stem) for stem in stems]
        if any(status in ("matched", "editorial") for status in statuses):
            matched_forms += 1
        elif stems:
            missing_only_forms += 1
        if len(stems) > 1:
            ambiguous_forms += 1
        if "-" in form:
            hyphenated_forms += 1

    return {
        "input_forms": len(words),
        "recognized_forms": len(form_index),
        "matched_forms": matched_forms,
        "missing_only_forms": missing_only_forms,
        "ambiguous_forms": ambiguous_forms,
        "hyphenated_forms": hyphenated_forms,
        "unresolved_forms": len(words) - len(form_index),
    }


def make_audit(
    source_records: List[Dict],
    words: List[str],
    da_words: List[Dict],
    entries: List[Dict],
    hunspell_data: Dict,
    lemmas: List[Dict],
    preao_stats: Dict[str, int],
    coverage: Dict[str, int],
    bridges: Optional[List[Dict]] = None,
) -> Dict:
    matched = [record for record in lemmas if record["status"] == "matched"]
    missing = [record for record in lemmas if record["status"] == "missing"]
    editorial = [record for record in lemmas if record["status"] == "editorial"]

    match_types = Counter(
        record["match"]["type"] for record in matched if record["match"]
    )
    if editorial:
        match_types["editorial"] = len(editorial)
    missing_pos = Counter()
    missing_priority = Counter()
    missing_source = Counter()
    for record in missing:
        missing_priority[record.get("priority", 3)] += 1
        for source in record["source"].split("+"):
            missing_source[source] += 1
        if record["pos"]:
            for category in record["pos"]:
                missing_pos[category] += 1
        else:
            missing_pos["unknown"] += 1

    curated_lemmas = [
        record for record in lemmas
        if "curated" in record["source"].split("+")
    ]
    curated_missing = [
        record for record in curated_lemmas
        if record["status"] == "missing"
    ]
    curated_matched = [
        record for record in curated_lemmas
        if record["status"] == "matched"
    ]
    curated_editorial = [
        record for record in curated_lemmas
        if record["status"] == "editorial"
    ]

    flags = collect_flag_counts(entries)

    rng = random.Random(20261108)
    missing_samples = rng.sample(
        missing, min(40, len(missing))
    ) if missing else []

    counts = {
        "words_pt_forms": len(words),
        "words_pt_unique": len(set(words)),
        "da_word_rows": len(da_words),
        "da_entries": len(entries),
        "da_senses": sum(len(entry["senses"]) for entry in entries),
        "hunspell_base_entries": len(hunspell_data["base"]),
        "hunspell_explicit_forms": len(hunspell_data["forms"]),
        "hunspell_proper_nouns": len(hunspell_data["proper_nouns"]),
        "hunspell_siglas": len(hunspell_data["siglas"]),
        "hunspell_punctuation": len(hunspell_data["punctuation"]),
        "lemma_universe": len(lemmas),
        "curated_lemmas": len(curated_lemmas),
        "curated_lemmas_missing": len(curated_missing),
        "curated_lemmas_matched": len(curated_matched),
        "curated_lemmas_editorial": len(curated_editorial),
        "lemmas_matched": len(matched),
        "lemmas_editorial": len(editorial),
        "lemmas_missing": len(missing),
        "missing_with_near_da": sum(
            1 for record in missing if record.get("near_da")
        ),
        "missing_ratio_percent": round(
            len(missing) / len(lemmas) * 100, 2
        ) if lemmas else 0.0,
    }

    wikt_section: Dict[str, object] = {
        "entries": 0,
        "senses": 0,
        "br_entries": 0,
        "exact": 0,
        "preao90": 0,
    }
    if bridges:
        wikt_section = {
            "entries": len(bridges),
            "senses": sum(len(bridge["senses"]) for bridge in bridges),
            "br_entries": sum(
                1 for bridge in bridges if bridge["status"] == "br"
            ),
            "exact": sum(
                1 for bridge in bridges if bridge["match"] == "exact"
            ),
            "preao90": sum(
                1 for bridge in bridges if bridge["match"] == "preao90"
            ),
        }
        counts["wikt_bridged"] = wikt_section["entries"]
        counts["wikt_bridged_senses"] = wikt_section["senses"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": source_records,
        "counts": counts,
        "wikt": wikt_section,
        "preao": preao_stats,
        "match_types": dict(sorted(match_types.items())),
        "missing_by_pos": dict(
            sorted(missing_pos.items(), key=lambda item: (-item[1], item[0]))
        ),
        "missing_by_priority": dict(
            sorted(missing_priority.items(), key=lambda item: item[0])
        ),
        "missing_by_source": dict(
            sorted(missing_source.items(), key=lambda item: item[0])
        ),
        "flags": flags,
        "coverage": coverage,
        "words_pt_stats": basic_stats(words),
        "missing_samples": [
            {
                "lemma": record["lemma"],
                "pos": record["pos"],
                "preao90": record["preao90"],
                "near_da": record.get("near_da"),
                "priority": record.get("priority", 3),
                "notes": record["notes"],
            }
            for record in missing_samples
        ],
    }


def write_report(
    docs_dir: Path,
    audit: Dict,
    lemmas: List[Dict],
    missing: List[Dict],
    source_records: List[Dict],
) -> None:
    counts = audit["counts"]
    flags = audit["flags"]
    coverage = audit["coverage"]
    match_types = audit["match_types"]
    missing_by_pos = audit["missing_by_pos"]

    sample_lemmas = [
        "ação",
        "atual",
        "ativo",
        "objeto",
        "ótimo",
        "comboio",
        "autocarro",
        "telemóvel",
        "frigorífico",
        "abafante",
        "abrangência",
        "acessar",
        "utilizador",
    ]
    by_lower = {record["lower"]: record for record in lemmas}
    sample_rows = []
    for lemma in sample_lemmas:
        record = by_lower.get(lemma)
        if not record:
            sample_rows.append("| `%s` | — | — | not in lemma universe |" % lemma)
            continue
        if record["status"] == "matched":
            sample_rows.append(
                "| `%s` | matched | %s | `%s` (id %s) |"
                % (
                    lemma,
                    record["match"]["type"],
                    record["match"]["headword"],
                    record["match"]["entry_id"],
                )
            )
        elif record["status"] == "editorial":
            sample_rows.append(
                "| `%s` | editorial | approved definition | — |"
                % lemma
            )
        else:
            wikt_info = record.get("wikt")
            extra = (
                " (wikt bridge: `%s`)" % wikt_info["headword"]
                if wikt_info
                else ""
            )
            sample_rows.append(
                "| `%s` | missing%s | — | %s |"
                % (lemma, extra, record["notes"])
            )

    missing_sample_lines = []
    for record in audit["missing_samples"][:30]:
        near = record.get("near_da")
        near_text = (
            "; near: `%s`" % near["headword"] if near else ""
        )
        missing_sample_lines.append(
            "- `%s` — %s%s%s"
            % (
                record["lemma"],
                ", ".join(record["pos"]) or "unknown",
                ("; " + record["notes"]) if record["notes"] else "",
                near_text,
            )
        )

    near_lemmas = [record for record in missing if record.get("near_da")]
    near_lines = []
    for record in near_lemmas[:30]:
        near = record["near_da"]
        near_lines.append(
            "- `%s` → `%s` (id %s)"
            % (record["lemma"], near["headword"], near["entry_id"])
        )

    wikt = audit.get("wikt") or {}
    wikt_stats_lines = [
        "| Measure | Count |",
        "| --- | ---: |",
        "| Missing lemmas with a bridge definition | %s |"
        % f"{wikt.get('entries', 0):,}",
        "| Bridge senses | %s |" % f"{wikt.get('senses', 0):,}",
        "| Matched on the modern (AO90) spelling | %s |"
        % f"{wikt.get('exact', 0):,}",
        "| Matched through the pre-AO spelling | %s |"
        % f"{wikt.get('preao90', 0):,}",
        "| Entries with only Brazilian-labelled senses (`br`) | %s |"
        % f"{wikt.get('br_entries', 0):,}",
    ]
    bridge_records = [
        record for record in missing if record.get("wikt")
    ]
    rng = random.Random(20261110)
    wikt_samples = rng.sample(bridge_records, min(15, len(bridge_records)))
    wikt_sample_lines = []
    for record in wikt_samples:
        info = record["wikt"]
        wikt_sample_lines.append(
            "- `%s` → snapshot headword `%s` (%s, %s senses)"
            % (
                record["lemma"],
                info["headword"],
                info["match"],
                info["senses"],
            )
        )
    if not wikt_sample_lines:
        wikt_sample_lines.append("- none")

    curated_missing = [
        record for record in missing
        if "curated" in record["source"].split("+")
    ]
    curated_lines = []
    for record in curated_missing:
        curated_lines.append(
            "- `%s` — %s%s"
            % (
                record["lemma"],
                record.get("curated_note", "") or "curated supplement",
                ("; " + record["notes"]) if record["notes"] else "",
            )
        )

    pos_lines = []
    for pos, count in list(missing_by_pos.items())[:20]:
        pos_lines.append("| `%s` | %s |" % (pos, count))

    source_lines = []
    for source in source_records:
        source_lines.append(
            "| %s | `%s` | `%s` | %s |"
            % (
                source["name"],
                source["filename"],
                source["sha256"][:16],
                source["licence"],
            )
        )

    report = """# Lexi2 corpus report

Generated by `scripts/build_corpus.py` from the pinned snapshots in
`docs/SOURCES.md`. This is an engineering and data-quality report, not a
lexicographic certification.

## Snapshots

| Source | File | SHA-256 (first 16) | Licence |
| --- | --- | --- | --- |
%s

## Corpus counts

| Measure | Count |
| --- | ---: |
| words-pt unique forms | %s |
| words-pt hyphenated forms | %s |
| Dicionário Aberto word rows | %s |
| Dicionário Aberto entries | %s |
| Dicionário Aberto senses | %s |
| Hunspell base entries | %s |
| Hunspell explicit inflected forms | %s |
| Modern lemma universe | %s |
| Curated supplement lemmas | %s |
| Curated supplement matched to Dicionário Aberto | %s |
| Curated supplement editorial definitions | %s |
| Editorial definitions | %s |
| Lemmas matched to Dicionário Aberto | %s |
| Lemmas missing | %s |
| Missing lemmas with a near DA candidate | %s |
| Lemmas covered by the Wiktionary bridge | %s |
| Missing ratio | %s%% |

## Match types

| Match | Lemmas |
| --- | ---: |
%s

`exact` means the modern lemma is a Dicionário Aberto headword. `preao90` uses
the Hunspell pre-AO spelling or the Natura spelling pairs. `supplement` uses a
reviewed pair from `sources/preao-supplement.txt`. `orthographic` covers hyphen
and spacing variants (for example `antirracista` / `anti-racista`), not
consonant guesses. `accent` means the difference is accentuation only (for
example `comboio` / `combóio`); it is still a source-text match that should be
reviewed when the accent could change meaning. Broad consonant guesses appear
only as unlinked near candidates.

## Sample lemmas

| Lemma | Status | Match type | Dicionário Aberto headword |
| --- | --- | --- | --- |
%s

## Missing lemmas

The primary missing-word deliverable is the lemma-only list in
`docs/missing-lemmas.csv` and `docs/missing-lemmas.json`. It excludes proper
nouns, siglas, punctuation and prefixes by default. A lemma with no Dicionário
Aberto match is not proof that the word is absent from Portuguese; it may be a
modern coinage, a technical term, a regional form or an unhandled spelling.

Top parts of speech:

| POS | Missing lemmas |
| --- | ---: |
%s

Missing-list priority: M1 = near DA candidate or pre-AO spelling; M2 = modern
Natura/AO lemma; M3 = other.

| Priority | Lemmas |
| --- | ---: |
%s

Deterministic sample:

%s

### Curated supplement

`sources/curated-lemmas.txt` adds a small, reviewed set of PT-PT lemmas that are
absent from the Hunspell base list. Their notes are review hints, not
definitions. The pipeline adds them to the missing universe and never invents a
definition.

%s

### Near candidates (not auto-linked)

The broad consonant rules can suggest a Dicionário Aberto headword for a
missing lemma, but they are not used for automatic attribution. These pairs must
be reviewed before a definition is reused. The full list is in the
`near_da_headword` column of `docs/missing-lemmas.csv`.

%s

## Wiktionary bridge layer

Missing lemmas that also exist in the sibling Lexi snapshot (Portuguese and
English Wiktionary via kaikki.org, wiktextract; CC BY-SA 4.0) carry a
labelled, unreviewed definition layer in the PWA. Senses are flagged `wikt`,
never merged into Dicionário Aberto, and shown with an explicit unreviewed
notice. The explicit `BR` marks of the snapshot are preserved and a
conservative parenthetical-label scan (`(Brazil`, `(Brasil`) marks further
senses; unmarked senses are not claimed to be European Portuguese. Where the
snapshot had applied its own unrevised automatic PT-PT adaptation, the build
restores the original wording and keeps the adapted text as a separately
flagged suggestion.

%s

Deterministic sample:

%s

The bridge is an import of published third-party content, not a linguistic
review and not an inference of new meanings. It does not change the missing
list: these lemmas still have no Dicionário Aberto entry.

## Review flags

Dicionário Aberto is historical. The pipeline preserves the original definition
and adds flags rather than silently correcting it.

| Flag | Senses | Entries |
| --- | ---: | ---: |
| Brazilian (`Bras`) | %s | %s |
| Regional | %s | %s |
| Archaic / obsolete | %s | %s |
| Technical | %s | %s |
| Popular / slang | %s | %s |
| Poetic | %s | %s |
| Neologism | %s | %s |

| Additional signal | Senses |
| --- | ---: |
| Pre-AO-looking spelling | %s |
| Automatic modernization available | %s |
| Automatic replacements | %s |
| Needs review | %s |
| Contains a citation or quotation | %s |
| Contains an example marker | %s |

Review priority (P1 = archaic/old spelling/citation; P2 = Brazilian, regional or
technical; P3 = no automatic warning):

| Priority | Senses |
| --- | ---: |
| P1 | %s |
| P2 | %s |
| P3 | %s |

The automatic modernization is a suggestion. It is never presented as a
human-reviewed definition, and the original text remains available.

## words-pt coverage

This raw diagnostic counts only direct Dicionário Aberto headwords, safe surface
variants, accent matches and explicit `.dic` forms. It does not use the full
Hunspell stem index; the form index below is the authoritative runtime
coverage.

| Measure | Forms |
| --- | ---: |
| Exact Dicionário Aberto headword | %s |
| Orthographic Dicionário Aberto match | %s |
| Accent-only Dicionário Aberto match | %s |
| Review candidate only (not attributed) | %s |
| Explicit Hunspell form | %s |
| Explicit Hunspell form with DA lemma | %s |
| Hunspell base lemma | %s |
| Hunspell base lemma with DA lemma | %s |
| Hyphenated forms | %s |
| Hyphenated forms resolved to a known base | %s |
| Unresolved by this diagnostic | %s |

Most hyphenated words-pt forms are enclitic verb forms. The raw wordlist
diagnostic above is not the runtime form index.

## Hunspell form index

`build/forms.json` maps a form to its Hunspell stem candidates. It is generated
with the build-time `hunspell -s` command and is not part of the runtime.

| Measure | Forms |
| --- | ---: |
| Input words-pt forms | %s |
| Recognized by Hunspell | %s |
| Forms with a matched lemma | %s |
| Forms with only a missing lemma | %s |
| Ambiguous forms (more than one stem) | %s |
| Hyphenated forms recognized | %s |
| Unresolved by Hunspell | %s |

The index still needs review for ambiguous stems, irregular verbs and forms that
Hunspell does not recognise. A stem is a lemma candidate, not a definition.

## Method and limitations

- The lemma universe comes from Hunspell pt_PT base entries, not from words-pt,
  because words-pt does not expose lemma identity. The Hunspell base list is not
  exhaustive: common modern words such as `utilizador` are absent from it, so
  they cannot appear in this first missing list without an additional reviewed
  lemma source.
- Dicionário Aberto is a 1913 dictionary. It lacks many modern terms and often
  uses pre-AO spelling. The missing list is therefore expected to contain real
  gaps and some spelling edge cases.
- Automatic matching uses exact headwords, authoritative `PREAO90` and Natura
  spelling pairs, accent-only equality, and hyphen/spacing variants. Broad
  consonant rules are used only to suggest near candidates for manual review;
  they never attach a definition automatically. This avoids false pairs such as
  `mosca`/`moca` or `micto`/`mito`.
- A near candidate is not a match. It may be a genuine old spelling (for example
  `absorção` / `absorpção`) or an unrelated word; the reviewer must decide.
- Brazilian and regional senses are preserved and labelled. European Portuguese
  is the default presentation decision for the future PWA, not a reason to
  delete source material.
- No definition has been human-reviewed. The flags identify where review is
  most needed.
- Hunspell's base list occasionally contains a plural or inflected form. The form
  index usually resolves it to the singular, but such a form can still appear in
  the missing list and should be rejected during review.
- The live Dicionário Aberto API is not the build source. The pinned 2015 dump is.
""" % (
        "\n".join(source_lines),
        f"{counts['words_pt_unique']:,}",
        f"{audit['words_pt_stats']['hyphenated']:,}",
        f"{counts['da_word_rows']:,}",
        f"{counts['da_entries']:,}",
        f"{counts['da_senses']:,}",
        f"{counts['hunspell_base_entries']:,}",
        f"{counts['hunspell_explicit_forms']:,}",
        f"{counts['lemma_universe']:,}",
        f"{counts['curated_lemmas']:,}",
        f"{counts['curated_lemmas_matched']:,}",
        f"{counts['curated_lemmas_editorial']:,}",
        f"{counts['lemmas_editorial']:,}",
        f"{counts['lemmas_matched']:,}",
        f"{counts['lemmas_missing']:,}",
        f"{counts['missing_with_near_da']:,}",
        f"{counts.get('wikt_bridged', 0):,}",
        f"{counts['missing_ratio_percent']:.2f}",
        "\n".join(
            "| %s | %s |" % (key, value)
            for key, value in sorted(match_types.items())
        ),
        "\n".join(sample_rows),
        "\n".join(pos_lines),
        "\n".join(
            "| M%s | %s |" % (key, value)
            for key, value in audit["missing_by_priority"].items()
        ),
        "\n".join(missing_sample_lines) or "- none",
        "\n".join(curated_lines) or "- none",
        "\n".join(near_lines) or "- none",
        "\n".join(wikt_stats_lines),
        "\n".join(wikt_sample_lines),
        f"{flags['senses_by_label']['brazil']:,}",
        f"{flags['entries_by_label']['brazil']:,}",
        f"{flags['senses_by_label']['regional']:,}",
        f"{flags['entries_by_label']['regional']:,}",
        f"{flags['senses_by_label']['archaic']:,}",
        f"{flags['entries_by_label']['archaic']:,}",
        f"{flags['senses_by_label']['technical']:,}",
        f"{flags['entries_by_label']['technical']:,}",
        f"{flags['senses_by_label']['popular']:,}",
        f"{flags['entries_by_label']['popular']:,}",
        f"{flags['senses_by_label']['poetic']:,}",
        f"{flags['entries_by_label']['poetic']:,}",
        f"{flags['senses_by_label']['neologism']:,}",
        f"{flags['entries_by_label']['neologism']:,}",
        f"{flags['old_spelling_senses']:,}",
        f"{flags['modernized_senses']:,}",
        f"{flags['modernization_replacements']:,}",
        f"{flags['needs_review_senses']:,}",
        f"{flags['citation_senses']:,}",
        f"{flags['example_senses']:,}",
        f"{flags['review_priority'].get('1', 0):,}",
        f"{flags['review_priority'].get('2', 0):,}",
        f"{flags['review_priority'].get('3', 0):,}",
        f"{coverage['exact_da_headword']:,}",
        f"{coverage['orthographic_da_match']:,}",
        f"{coverage['accent_da_match']:,}",
        f"{coverage['review_candidate_only']:,}",
        f"{coverage['explicit_hunspell_form']:,}",
        f"{coverage['explicit_hunspell_form_with_da_lemma']:,}",
        f"{coverage['hunspell_base_lemma']:,}",
        f"{coverage['hunspell_base_lemma_with_da_lemma']:,}",
        f"{coverage['hyphenated']:,}",
        f"{coverage['hyphenated_resolved']:,}",
        f"{coverage['unresolved']:,}",
        f"{audit.get('forms', {}).get('input_forms', 0):,}",
        f"{audit.get('forms', {}).get('recognized_forms', 0):,}",
        f"{audit.get('forms', {}).get('matched_forms', 0):,}",
        f"{audit.get('forms', {}).get('missing_only_forms', 0):,}",
        f"{audit.get('forms', {}).get('ambiguous_forms', 0):,}",
        f"{audit.get('forms', {}).get('hyphenated_forms', 0):,}",
        f"{audit.get('forms', {}).get('unresolved_forms', 0):,}",
    )

    (docs_dir / "CORPUS.md").write_text(report, encoding="utf-8")


def write_m1_report(docs_dir: Path, missing: List[Dict]) -> None:
    """Write a focused review queue for the high-priority missing lemmas."""

    m1 = [record for record in missing if record.get("priority") == 1]
    groups: Dict[str, List[Dict]] = {
        "curated": [],
        "near_and_preao": [],
        "near": [],
        "preao": [],
        "other": [],
    }
    for record in m1:
        has_near = bool(record.get("near_da"))
        has_pre = bool(record.get("preao90"))
        if "curated" in record["source"].split("+"):
            groups["curated"].append(record)
        elif has_near and has_pre:
            groups["near_and_preao"].append(record)
        elif has_near:
            groups["near"].append(record)
        elif has_pre:
            groups["preao"].append(record)
        else:
            groups["other"].append(record)

    def line(record: Dict) -> str:
        bits = [
            "`%s`" % record["lemma"],
            " | ".join(record["pos"]) or "unknown",
            record["source"],
        ]
        if record.get("preao90"):
            bits.append("pre-AO: `%s`" % record["preao90"])
        near = record.get("near_da")
        if near:
            bits.append("near: `%s`" % near["headword"])
        if record.get("curated_note"):
            bits.append("note: %s" % record["curated_note"])
        wikt_info = record.get("wikt")
        if wikt_info:
            bits.append(
                "wikt bridge: «%s» (%s)" % (wikt_info["headword"], wikt_info["match"])
            )
        if record.get("notes"):
            bits.append(record["notes"])
        return "- " + "; ".join(bits)

    sections = [
        ("Curated supplement", groups["curated"],
         "All 22 curated supplement lemmas now have approved editorial definitions "
         "in `sources/curated-definitions.txt`. If this group is non-empty, write "
         "a reviewed PT-PT definition or confirm that the lemma should remain "
         "missing."),
        ("Near candidate and pre-AO spelling", groups["near_and_preao"],
         "A near DA headword and a pre-AO spelling both exist. Check the candidate "
         "before adding a pair to `sources/preao-supplement.txt`."),
        ("Near candidate only", groups["near"],
         "The 19 reviewed near-only lemmas now have approved editorial "
         "definitions in `sources/curated-definitions.txt`; their rejected "
         "old-spelling candidates remain recorded in "
         "`sources/preao-supplement.txt`. If this group is non-empty, review the "
         "new candidate before adding a definition or mapping."),
        ("Pre-AO spelling only", groups["preao"],
         "The modern lemma has a pre-AO spelling, but that spelling is also absent "
         "from Dicionário Aberto. This is likely a genuine definition gap. "
         "Proposed definitions for the 35 highest-value lemmas in this group are "
         "in `docs/M1-PROPOSED-BATCH.md`; they stay unintegrated until approved."),
        ("Other", groups["other"],
         "No automatic candidate. Handle as a normal missing lemma."),
    ]

    lines = [
        "# M1 missing lemmas",
        "",
        "Generated by `scripts/build_corpus.py` from `docs/missing-lemmas.csv`.",
        "M1 is the highest review priority: a curated supplement lemma, a near DA",
        "candidate, or a known pre-AO spelling. A pair is not a definition; the",
        "reviewer decides whether to add a spelling mapping or write a definition.",
        "",
        "The reviewed `sources/preao-supplement.txt` resolved 149 modern lemmas",
        "through genuine old spellings. The 22 curated lemmas and the 19 reviewed",
        "near-only lemmas now have approved editorial definitions in",
        "`sources/curated-definitions.txt`.",
        "The remaining M1 queue is %s lemmas. Proposed definitions for the 35" % len(m1),
        "highest-value pre-AO-only lemmas are in `docs/M1-PROPOSED-BATCH.md` and",
        "are not integrated.",
        "",
        "Of these, %s lemmas carry a Wiktionary bridge definition in the PWA"
        % sum(1 for record in m1 if record.get("wikt")),
        "(flagged `wikt`, unreviewed third-party content). The Dicionário Aberto",
        "gap itself remains: review the imported text or write a PT-PT definition.",
        "",
        "| Group | Lemmas |",
        "| --- | ---: |",
    ]
    for title, records, _description in sections:
        lines.append("| %s | %s |" % (title, len(records)))
    lines.append("| **Total** | **%s** |" % len(m1))
    lines.append("")

    for title, records, description in sections:
        lines.append("## %s (%s)" % (title, len(records)))
        lines.append("")
        lines.append(description)
        lines.append("")
        if records:
            lines.extend(line(record) for record in records)
        else:
            lines.append("- none")
        lines.append("")

    lines.extend(
        [
            "## Recommended order",
            "",
            "1. Pre-AO-only lemmas: confirm the gap and write a new definition or",
            "   keep the lemma in the missing list with a note.",
            "2. Use the word-list and PDF coverage reports to prioritise the",
            "   pre-AO-only lemmas that occur in real running text.",
            "3. Add new old-spelling mappings only after review, in",
            "   `sources/preao-supplement.txt`.",
            "",
            "The PDF/word-list coverage reports can show which of these lemmas occur in",
            "real running text and should be prioritised.",
            "",
        ]
    )

    (docs_dir / "M1-MISSING.md").write_text("\n".join(lines), encoding="utf-8")


def compare_audits(existing: Dict, current: Dict) -> List[str]:
    differences: List[str] = []
    for section in ("counts", "preao", "match_types", "flags", "coverage", "wikt"):
        old = existing.get(section)
        new = current.get(section)
        if old != new:
            differences.append(section)
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources-dir",
        default=str(DEFAULT_SOURCES),
        help="Downloaded snapshots directory (default: .work/sources)",
    )
    parser.add_argument(
        "--build-dir",
        default=str(DEFAULT_BUILD),
        help="Intermediate output directory (default: build)",
    )
    parser.add_argument(
        "--docs-dir",
        default=str(ROOT / "docs"),
        help="Documentation directory (default: docs)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Recompute and compare with build/audit.json without writing",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not regenerate docs/CORPUS.md",
    )
    parser.add_argument(
        "--no-forms",
        action="store_true",
        help="Skip the Hunspell form-to-lemma index",
    )
    args = parser.parse_args()

    sources_dir = Path(args.sources_dir).resolve()
    build_dir = Path(args.build_dir).resolve()
    docs_dir = Path(args.docs_dir).resolve()

    print("Verifying source snapshots...")
    source_records = verify_sources(sources_dir, require_extracted=True)

    words_path = sources_dir / "wordsList"
    da_path = sources_dir / "da.sql"
    dic_path = find_hunspell(sources_dir)
    ao_path = sources_dir / "wordlist-ao.txt"
    pre_path = sources_dir / "wordlist-preao.txt"

    print("Loading words-pt...")
    words = load_words(str(words_path))
    words_lower = lower_set(words)

    print("Loading Natura AO and pre-AO lists...")
    ao_words = load_plain_list(ao_path)
    pre_words = load_plain_list(pre_path)
    ao_set = lower_set(ao_words)
    pre_set = lower_set(pre_words)

    print("Loading Hunspell pt_PT...")
    hunspell_data = parse_dic(str(dic_path))

    print("Deriving pre-AO -> AO pairs...")
    preao_supplement = load_preao_supplement(
        ROOT / "sources" / "preao-supplement.txt"
    )
    pre_to_ao, pre_only, modern_words, preao_stats = make_preao_map(
        pre_words, ao_words, hunspell_data, preao_supplement
    )

    print("Parsing Dicionário Aberto...")
    da_words, revisions = load_da(str(da_path))

    print("Building entries, flags and modernization suggestions...")
    entries = build_entries(
        da_words,
        revisions,
        pre_to_ao,
        pre_only,
        modern_words,
    )
    entries_by_id = {entry["id"]: entry for entry in entries}

    print("Building DA indexes...")
    indexes = build_indexes(entries, preao_supplement)

    print("Loading curated lemma supplement...")
    curated_lemmas = load_curated_lemmas(
        ROOT / "sources" / "curated-lemmas.txt"
    )
    curated_definitions = load_curated_definitions(
        ROOT / "sources" / "curated-definitions.txt"
    )

    print("Matching the modern lemma universe...")
    lemmas = build_lemmas(
        hunspell_data,
        words_lower,
        ao_set,
        pre_set,
        indexes,
        entries_by_id,
        curated_lemmas,
        curated_definitions,
    )
    matched = [record for record in lemmas if record["status"] == "matched"]
    missing = [record for record in lemmas if record["status"] == "missing"]

    print("Matching the Wiktionary bridge snapshot...")
    wikt_entries = load_wikt_entries(sources_dir)
    bridges: List[Dict] = []
    for record in missing:
        found = match_wikt_entry(
            record["lemma"], record.get("preao90"), wikt_entries
        )
        if not found:
            continue
        match_type, wikt_entry = found
        row = wikt_build_row(record["lemma"], match_type, wikt_entry)
        if not row:
            continue
        record["wikt"] = {
            "headword": wikt_entry["headword"],
            "match": match_type,
            "senses": len(row["senses"]),
        }
        record["notes"] = ";".join(
            part
            for part in (record["notes"].split(";") + ["wikt_bridge"])
            if part
        )
        bridges.append(
            {
                "lemma": record["lemma"],
                "lower": record["lower"],
                "pos": record["pos"],
                "match": match_type,
                "wikt_headword": wikt_entry["headword"],
                "pos_display": row["pos"],
                "senses": row["senses"],
                "status": row["status"],
            }
        )
    print(
        "Wiktionary bridge: %s missing lemmas covered"
        % f"{len(bridges):,}"
    )

    print("Calculating words-pt coverage...")
    hunspell_forms = build_form_index(hunspell_data["forms"])
    hunspell_base_lemmas = {
        record["word"].lower()
        for record in hunspell_data["base"]
        if is_lexical_lemma(record)
    }
    lemma_status = {
        record["lower"]: record["status"] for record in lemmas
    }

    form_index: Dict[str, List[str]] = {}
    form_stats: Dict[str, int] = {}
    if not args.no_forms:
        if not hunspell_available():
            raise RuntimeError(
                "hunspell is required for the form index; install it or use "
                "--no-forms"
            )
        print("Building Hunspell form index...")
        allowed_stems = set(lemma_status) | set(indexes["exact"])
        form_index = build_stem_index(
            words,
            str(dic_path.with_suffix("")),
            allowed_stems,
        )
        # The .dic also carries explicit irregular and suppletive forms that
        # ``hunspell -s`` does not always recover (for example foi -> ser/ir).
        form_index = {
            form: set(stems) for form, stems in form_index.items()
        }
        for form, stems in hunspell_forms.items():
            allowed = {
                stem.lower()
                for stem in stems
                if stem.lower() in allowed_stems
            }
            if allowed:
                form_index.setdefault(form, set()).update(allowed)
        form_index = {
            form: sorted(stems)
            for form, stems in form_index.items()
        }
        form_stats = form_index_stats(form_index, words, lemma_status)

    coverage = words_coverage(
        words,
        indexes,
        hunspell_forms,
        hunspell_base_lemmas,
        lemma_status,
    )

    audit = make_audit(
        source_records,
        words,
        da_words,
        entries,
        hunspell_data,
        lemmas,
        preao_stats,
        coverage,
        bridges,
    )
    audit["forms"] = form_stats

    if args.check:
        audit_path = build_dir / "audit.json"
        if not audit_path.exists():
            print("error: %s does not exist" % audit_path, file=sys.stderr)
            return 1
        existing = json.loads(audit_path.read_text(encoding="utf-8"))
        differences = compare_audits(existing, audit)
        if differences:
            print("Audit mismatch in: %s" % ", ".join(differences))
            for section in differences:
                print("\n%s:" % section)
                print("  existing:", existing.get(section))
                print("  current: ", audit.get(section))
            return 1
        print("Audit matches %s" % audit_path)
        return 0

    build_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("Writing %s" % (build_dir / "da-entries.jsonl"))
    write_jsonl(build_dir / "da-entries.jsonl", entries)
    print("Writing %s" % (build_dir / "lemmas.jsonl"))
    write_jsonl(build_dir / "lemmas.jsonl", lemmas)
    print("Writing %s" % (build_dir / "wikt-bridges.jsonl"))
    write_jsonl(build_dir / "wikt-bridges.jsonl", bridges)
    print("Writing %s" % (docs_dir / "missing-lemmas.csv"))
    write_missing_files(docs_dir, missing)
    print("Writing %s" % (build_dir / "audit.json"))
    (build_dir / "audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (build_dir / "words-pt-coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (build_dir / "preao-pairs.json").write_text(
        json.dumps(pre_to_ao, indent=0, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if form_index:
        print("Writing %s" % (build_dir / "forms.json"))
        (build_dir / "forms.json").write_text(
            json.dumps(form_index, ensure_ascii=False, indent=0) + "\n",
            encoding="utf-8",
        )
        (build_dir / "forms-meta.json").write_text(
            json.dumps(form_stats, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if not args.no_report:
        print("Writing %s" % (docs_dir / "CORPUS.md"))
        write_report(
            docs_dir,
            audit,
            lemmas,
            missing,
            source_records,
        )
        print("Writing %s" % (docs_dir / "M1-MISSING.md"))
        write_m1_report(docs_dir, missing)

    print()
    print("Lemmas: %s matched, %s missing (%.2f%%)"
          % (
              f"{len(matched):,}",
              f"{len(missing):,}",
              (len(missing) / len(lemmas) * 100) if lemmas else 0.0,
          ))
    print("Entries: %s; senses: %s"
          % (
              f"{len(entries):,}",
              f"{audit['counts']['da_senses']:,}",
          ))
    print("Missing list: %s" % (docs_dir / "missing-lemmas.csv"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - command-line tool
        print("error: %s" % error, file=sys.stderr)
        raise
