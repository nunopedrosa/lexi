#!/usr/bin/env python3
"""Convert the built corpus into compact, sharded PWA data.

Inputs (from build_corpus.py):
  build/da-entries.jsonl
  build/lemmas.jsonl
  build/wikt-bridges.jsonl
  build/forms.json
  build/audit.json

Outputs:
  data/meta.json
  data/<key>.json
  data/forms-meta.json
  data/forms/<key>.json
  data/missing-meta.json
  data/missing/<key>.json
  data/regional.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.normalize import fold  # noqa: E402

KEYS = ["_"] + [chr(code) for code in range(ord("a"), ord("z") + 1)]


def key_of(word: str) -> str:
    first = fold(word)[:1]
    return first if first and "a" <= first <= "z" else "_"


def load_jsonl(path: Path) -> Iterable[Dict]:
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_lower_set(path: Path) -> Set[str]:
    with open(path, "r", encoding="iso-8859-1") as handle:
        return {line.strip().lower() for line in handle if line.strip()}


def compact_flags(sense: Dict) -> List[str]:
    labels = sense["label_flags"]
    flags: List[str] = []
    if labels["archaic"]:
        flags.append("arch")
    if labels["regional"]:
        flags.append("reg")
    if labels["technical"]:
        flags.append("tech")
    if labels["popular"]:
        flags.append("pop")
    if labels["poetic"]:
        flags.append("poet")
    if labels["neologism"]:
        flags.append("neo")
    if sense["spelling"]["has_old_spelling"]:
        flags.append("old")
    if sense["modernization"]["count"]:
        flags.append("mod")
    if sense["review"]["has_citation"]:
        flags.append("cit")
    if sense["review"]["needs_review"]:
        flags.append("rev")
    return flags


def clean_text(text: str) -> str:
    """Remove the source's inline emphasis markers while keeping its words."""

    text = text.replace("_", "")
    text = text.replace("[[", "").replace("]]", "")
    return " ".join(text.split())


def compact_sense(sense: Dict, source_headword: str) -> List:
    original = clean_text(sense["definition"])
    modernized = clean_text(sense["modernization"]["text"])
    if modernized == original:
        modernized = ""
    return [
        original,
        "BR" if sense["label_flags"]["brazil"] else "",
        compact_flags(sense),
        modernized,
        source_headword,
    ]


def build_rows(
    entries: List[Dict],
    lemmas: List[Dict],
    ao_set: Set[str],
    pre_set: Set[str],
) -> Dict[str, Dict]:
    """Merge DA entries under their modern lemma when one is available."""

    by_entry: Dict[int, List[Dict]] = defaultdict(list)
    for lemma in lemmas:
        if lemma["status"] == "matched" and lemma.get("match"):
            by_entry[lemma["match"]["entry_id"]].append(lemma)

    rows: Dict[str, Dict] = {}

    for entry in entries:
        matched = sorted(by_entry.get(entry["id"], []), key=lambda item: item["lower"])
        display = matched[0]["lemma"] if matched else entry["headword"]
        aliases = {entry["headword"]}
        for lemma in matched:
            aliases.add(lemma["lemma"])

        in_ptpt = (
            display.lower() in ao_set
            or display.lower() in pre_set
            or entry["headword"].lower() in ao_set
            or entry["headword"].lower() in pre_set
            or any(
                lemma["in_ao_list"] or lemma["in_preao_list"]
                for lemma in matched
            )
        )
        br_all = bool(entry["senses"]) and all(
            sense["label_flags"]["brazil"] for sense in entry["senses"]
        )
        status = "br" if br_all else "ok" if in_ptpt else "historical"

        row = rows.get(display)
        if row is None:
            row = {
                "headword": display,
                "pos": [],
                "senses": [],
                "aliases": set(),
                "statuses": set(),
            }
            rows[display] = row

        row["aliases"].update(aliases)
        row["statuses"].add(status)
        for sense in entry["senses"]:
            if sense["grammar"]:
                row["pos"].append(sense["grammar"])
        for sense in entry["senses"]:
            compact = compact_sense(sense, entry["headword"])
            if compact not in row["senses"]:
                row["senses"].append(compact)

    for row in rows.values():
        row["pos"] = " · ".join(dict.fromkeys(row["pos"]))
        row["aliases"] = sorted(row["aliases"])
        if "ok" in row["statuses"]:
            row["status"] = "ok"
        elif "br" in row["statuses"]:
            row["status"] = "br"
        else:
            row["status"] = "historical"

    return rows


def write_shards(
    directory: Path,
    meta_path: Path,
    records: List[Tuple[str, List]],
    meta_extra: Optional[Dict] = None,
) -> Dict[str, int]:
    directory.mkdir(parents=True, exist_ok=True)
    shards: Dict[str, List] = {key: [] for key in KEYS}
    for word, payload in records:
        shards[key_of(word)].append([word] + payload)

    counts: Dict[str, int] = {}
    total_bytes = 0
    for key in KEYS:
        rows = shards[key]
        rows.sort(key=lambda row: (fold(row[0]), row[0]))
        path = directory / ("%s.json" % key)
        path.write_text(
            json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        counts[key] = len(rows)
        total_bytes += path.stat().st_size

    meta = {
        "keys": KEYS,
        "shards": KEYS,
        "counts": counts,
        "total": sum(counts.values()),
        "bytes": total_bytes,
    }
    if meta_extra:
        meta.update(meta_extra)
    meta_path.write_text(
        json.dumps(meta, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", default=str(ROOT / "build"))
    parser.add_argument("--data-dir", default=str(ROOT / "data"))
    parser.add_argument(
        "--sources-dir",
        default=str(ROOT / ".work" / "sources"),
        help="Extracted source snapshots (for the PT-PT lexicon check)",
    )
    args = parser.parse_args()

    build_dir = Path(args.build_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    sources_dir = Path(args.sources_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    print("Loading entries and lemmas...")
    entries = list(load_jsonl(build_dir / "da-entries.jsonl"))
    lemmas = list(load_jsonl(build_dir / "lemmas.jsonl"))
    bridges = list(load_jsonl(build_dir / "wikt-bridges.jsonl"))
    audit = json.loads((build_dir / "audit.json").read_text(encoding="utf-8"))
    forms = json.loads((build_dir / "forms.json").read_text(encoding="utf-8"))

    print("Loading the modern PT-PT lexicon...")
    ao_set = load_lower_set(sources_dir / "wordlist-ao.txt")
    pre_set = load_lower_set(sources_dir / "wordlist-preao.txt")

    print("Merging entries under modern lemmas...")
    rows = build_rows(entries, lemmas, ao_set, pre_set)
    for lemma in lemmas:
        if lemma["status"] != "editorial":
            continue
        display = lemma["lemma"]
        if display in rows:
            continue
        # Editorial entries may carry a region label ("BR", Dicionário Aberto
        # convention): the entry is then fully tagged Brazilian and its status
        # becomes "br", while the definition text stays European Portuguese.
        region = (lemma.get("editorial_region") or "").strip().upper()
        rows[display] = {
            "headword": display,
            "pos": [lemma.get("editorial_pos") or "n."],
            "senses": [[
                lemma["editorial_definition"],
                region,
                ["editorial"],
                "",
                "",
            ]],
            "aliases": {display},
            "status": "br" if region == "BR" else "ok",
        }

    print("Adding the Wiktionary bridge layer...")
    wikt_added = 0
    for bridge in bridges:
        display = bridge["lemma"]
        if display in rows:
            # A Dicionário Aberto or editorial row already exists under this
            # headword; the bridge never overrides it.
            continue
        if not bridge.get("senses"):
            continue
        rows[display] = {
            "headword": display,
            "pos": bridge.get("pos_display") or "",
            "senses": [list(sense) for sense in bridge["senses"]],
            "aliases": {display},
            "status": bridge["status"],
        }
        wikt_added += 1

    print("Writing dictionary shards...")
    dictionary_records = [
        (
            row["headword"],
            [row["pos"], row["senses"], row["status"]],
        )
        for row in rows.values()
    ]
    dictionary_counts = write_shards(
        data_dir,
        data_dir / "meta.json",
        dictionary_records,
        {
            "headwords": len(rows),
            "senses": sum(len(row["senses"]) for row in rows.values()),
            "source": (
                "Dicionário Aberto (2015-12-13 snapshot) + Wiktionary bridge "
                "layer (see ATTRIBUTION.md)"
            ),
            "source_licence": "CC BY-SA 2.5 PT",
            "wikt_source": (
                "Wiktionary via kaikki.org (CC BY-SA 4.0); compiled in the "
                "sibling Lexi snapshot; senses flagged wikt"
            ),
            "form_index": "Hunspell pt_PT 2025-10-01",
            "missing_lemmas": audit["counts"]["lemmas_missing"],
            "editorial_definitions": audit["counts"]["lemmas_editorial"],
            "wikt_entries": wikt_added,
            "entry_status": dict(
                sorted(
                    Counter(row["status"] for row in rows.values()).items()
                )
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    print("Writing form-index shards...")
    # Map each Hunspell stem or DA headword to the display headword used above.
    grouped_by_entry: Dict[int, List[Dict]] = defaultdict(list)
    for lemma in lemmas:
        if lemma["status"] == "matched" and lemma.get("match"):
            grouped_by_entry[lemma["match"]["entry_id"]].append(lemma)
    entry_primary = {
        entry_id: sorted(items, key=lambda item: item["lower"])[0]["lemma"]
        for entry_id, items in grouped_by_entry.items()
    }

    stem_to_display: Dict[str, str] = {}
    for lemma in lemmas:
        if lemma["status"] == "editorial":
            stem_to_display[lemma["lower"]] = lemma["lemma"]
            continue
        if lemma["status"] == "missing":
            stem_to_display[lemma["lower"]] = lemma["lemma"]
            if lemma.get("preao90"):
                stem_to_display.setdefault(
                    lemma["preao90"].lower(), lemma["lemma"]
                )
            continue
        if lemma["status"] != "matched" or not lemma.get("match"):
            continue
        display = entry_primary.get(
            lemma["match"]["entry_id"], lemma["match"]["headword"]
        )
        stem_to_display[lemma["lower"]] = display
        stem_to_display[lemma["match"]["headword"].lower()] = display

    for row in rows.values():
        for alias in row["aliases"]:
            stem_to_display.setdefault(alias.lower(), row["headword"])

    display_set = set(rows)
    missing_display_set = {
        lemma["lemma"] for lemma in lemmas if lemma["status"] == "missing"
    }
    valid_display_set = display_set | missing_display_set
    display_lower = {display.lower() for display in valid_display_set}
    form_targets: Dict[str, List[str]] = {}
    form_case: Dict[str, str] = {}

    def display_for(value: str) -> Optional[str]:
        direct = stem_to_display.get(value.lower())
        if direct:
            return direct
        for stem in forms.get(value, []):
            direct = stem_to_display.get(stem.lower())
            if direct:
                return direct
        return None

    def add_target(form: str, display: str) -> None:
        if not form or not display:
            return
        key = form.lower()
        if key == display.lower():
            return
        if key in display_set:
            return
        form_case.setdefault(key, form)
        targets = form_targets.setdefault(key, [])
        if display not in targets:
            targets.append(display)

    for form in sorted(forms):
        for stem in forms[form]:
            display = stem_to_display.get(stem.lower())
            if display and display in valid_display_set:
                add_target(form, display)

    # Make the Dicionário Aberto source headwords searchable under the modern
    # display lemma (for example acção -> ação).
    for row in rows.values():
        for alias in row["aliases"]:
            if alias.lower() != row["headword"].lower():
                add_target(alias, row["headword"])

    # Add the Natura pre-AO spelling pairs (for example actividade -> atividade).
    preao_path = build_dir / "preao-pairs.json"
    if preao_path.exists():
        pre_to_ao = json.loads(preao_path.read_text(encoding="utf-8"))
        for pre, modern in pre_to_ao.items():
            display = display_for(modern)
            if display and display in valid_display_set:
                add_target(pre, display)

    form_rows: List[Tuple[str, List]] = []
    for key in sorted(form_targets):
        targets = form_targets[key]
        payload = targets[0] if len(targets) == 1 else targets
        form_rows.append((form_case[key], [payload]))

    form_counts = write_shards(
        data_dir / "forms",
        data_dir / "forms-meta.json",
        form_rows,
        {
            "source": "Hunspell pt_PT 2025-10-01 and Dicionário Aberto aliases",
            "note": (
                "Each row is [form, display] for one target or "
                "[form, [display, ...]] when ambiguous."
            ),
        },
    )

    print("Writing missing-lemma shards...")
    missing_records = []
    for lemma in lemmas:
        if lemma["status"] != "missing":
            continue
        near = lemma.get("near_da") or {}
        missing_records.append(
            (
                lemma["lemma"],
                [
                    lemma["pos"],
                    lemma["preao90"] or "",
                    near.get("headword", ""),
                    near.get("entry_id", ""),
                    lemma.get("notes", ""),
                    lemma.get("priority", 3),
                    lemma.get("source", ""),
                    lemma.get("curated_note", ""),
                    (lemma.get("wikt") or {}).get("headword", ""),
                ],
            )
        )
    missing_counts = write_shards(
        data_dir / "missing",
        data_dir / "missing-meta.json",
        missing_records,
        {
            "note": (
                "Lemmas with no Dicionário Aberto match after safe matching; "
                "field 10 names the Wiktionary bridge headword when the lemma "
                "is covered by that unreviewed layer."
            ),
        },
    )

    regional_source = ROOT / "sources" / "regional-ptpt-br.json"
    if regional_source.exists():
        regional = json.loads(regional_source.read_text(encoding="utf-8"))
    else:
        regional = {"terms": {}}
    (data_dir / "regional.json").write_text(
        json.dumps(regional, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    print()
    print("Dictionary: %s headwords, %s senses"
          % (f"{len(rows):,}", f"{sum(len(row['senses']) for row in rows.values()):,}"))
    print("Entry status: %s"
          % dict(sorted(Counter(row["status"] for row in rows.values()).items())))
    print("Forms: %s" % f"{len(form_rows):,}")
    print("Missing lemmas: %s" % f"{len(missing_records):,}")
    print("Shard counts: %s" % dictionary_counts)
    print("Form counts: %s" % form_counts)
    print("Missing counts: %s" % missing_counts)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("error: %s" % error, file=sys.stderr)
        raise
