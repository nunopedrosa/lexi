#!/usr/bin/env python3
"""Measure Lexi2 dictionary coverage on user-supplied Portuguese PDFs.

This is a build-time analysis tool. It extracts text, tokenises Portuguese words,
and classifies each token against the generated dictionary, form index and
missing-lemma list. PDFs are read in place and are not copied into the project.

The extractor is ``pypdf`` when available. A local copy can be installed with:

  python3 -m pip install --target .work/python pypdf

The report contains aggregate counts and token lists, not full document text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / ".work" / "python"))

from lib.normalize import fold  # noqa: E402

TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-\u2019'][^\W\d_]+)*", re.UNICODE)
MAX_TOKENS_DEFAULT = 2_000_000

# Common English function words and mixed-document vocabulary. A token is only
# treated as foreign after the Portuguese dictionary, form index and missing
# list have been checked, so Portuguese words that share a spelling are kept.
FOREIGN_WORDS = {
    "the", "of", "and", "or", "by", "with", "this", "that", "from", "for",
    "are", "is", "to", "in", "on", "at", "be", "it", "its", "not", "all",
    "any", "such", "may", "will", "shall", "under", "other", "which",
    "their", "after", "within", "without", "same", "third", "information",
    "project", "party", "parties", "agreement", "consortium", "grant",
    "rights", "section", "article", "annex", "version", "results",
    "background", "meeting", "authority", "obligations", "conditions",
    "control", "costs", "written", "granted", "decision", "implementation",
    "accordance", "defaulting", "confidential", "access", "user", "login",
    "dashboard", "welcome", "thank", "you", "your", "please", "enter",
    "already", "taken", "session", "code", "scan", "denied", "rotate",
    "device", "instructions", "avatar", "environmentalist", "construction",
    "correct", "answer", "submitted", "up", "connection", "lost", "return",
    "goodbye", "join", "leave", "admin", "onboarding", "overlay", "stage",
    "change", "congratulations", "kickar", "display", "name", "html",
    "score", "panel", "roll", "pick", "tile", "furnace", "timer", "times",
    "card", "board", "opinion", "pipe", "time", "online", "stop", "show",
    "design", "software", "hardware", "input", "medical", "pixel", "status",
    "performance", "quorum", "exclusive", "logos", "sensor", "tele",
}


def key_of(word: str) -> str:
    first = fold(word)[:1]
    return first if first and "a" <= first <= "z" else "_"


def normalise_text(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\u2019", "'"))


def extract_with_pypdf(path: Path, max_pages: int) -> Tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError(
            "pypdf is not installed. Run: python3 -m pip install "
            "--target .work/python pypdf"
        ) from error

    reader = PdfReader(str(path))
    pages = reader.pages[:max_pages]
    chunks = []
    for page in pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks), len(pages)


def extract_text(path: Path, max_pages: int) -> Tuple[str, int]:
    text, pages = extract_with_pypdf(path, max_pages)
    return normalise_text(text), pages


def collect_inputs(paths: List[Path]) -> List[Path]:
    found: List[Path] = []
    supported = {".pdf", ".txt", ".words"}
    for path in paths:
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in supported:
                    found.append(candidate)
        elif path.is_file() and path.suffix.lower() in supported:
            found.append(path)
    return found


def extract_input(path: Path, max_pages: int) -> Tuple[str, int, str]:
    if path.suffix.lower() == ".pdf":
        text, pages = extract_text(path, max_pages)
        return text, pages, "pdf"
    text = path.read_text(encoding="utf-8", errors="replace")
    return normalise_text(text), 0, "wordlist"


def load_dictionary(
    data_dir: Path,
    keys: Set[str],
) -> Tuple[Dict[str, int], Dict[str, List[str]], Dict[str, Dict]]:
    headwords: Dict[str, int] = {}
    forms: Dict[str, List[str]] = {}
    missing: Dict[str, Dict] = {}

    meta = json.loads((data_dir / "meta.json").read_text(encoding="utf-8"))
    for key in meta.get("keys", []):
        if key not in keys:
            continue
        path = data_dir / ("%s.json" % key)
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8")):
            headwords.setdefault(fold(row[0]), 0)
            headwords[fold(row[0])] += 1

    forms_meta_path = data_dir / "forms-meta.json"
    if forms_meta_path.exists():
        forms_meta = json.loads(forms_meta_path.read_text(encoding="utf-8"))
        for key in forms_meta.get("shards", []):
            if key not in keys:
                continue
            path = data_dir / "forms" / ("%s.json" % key)
            if not path.exists():
                continue
            for row in json.loads(path.read_text(encoding="utf-8")):
                payload = row[1]
                targets = payload if isinstance(payload, list) else [payload]
                forms.setdefault(fold(row[0]), []).extend(targets)

    missing_meta_path = data_dir / "missing-meta.json"
    if missing_meta_path.exists():
        missing_meta = json.loads(missing_meta_path.read_text(encoding="utf-8"))
        for key in missing_meta.get("shards", []):
            if key not in keys:
                continue
            path = data_dir / "missing" / ("%s.json" % key)
            if not path.exists():
                continue
            for row in json.loads(path.read_text(encoding="utf-8")):
                missing[fold(row[0])] = {
                    "lemma": row[0],
                    "pos": row[1],
                    "preao90": row[2],
                    "near": row[3],
                    "near_id": row[4],
                    "notes": row[5],
                    "priority": row[6],
                    "source": row[7],
                    "curated_note": row[8],
                }

    return headwords, forms, missing


def classify(
    token: str,
    headwords: Dict[str, int],
    forms: Dict[str, List[str]],
    missing: Dict[str, Dict],
) -> Tuple[str, Optional[str]]:
    folded = fold(token)
    if folded in headwords:
        return "headword", None
    if folded in missing:
        return "missing_lemma", missing[folded]["lemma"]
    targets = forms.get(folded)
    if targets:
        for target in targets:
            target_folded = fold(target)
            if target_folded in missing:
                return "missing_form", missing[target_folded]["lemma"]
        return "form", targets[0]
    if folded in FOREIGN_WORDS:
        return "foreign", None
    return "unknown", None


def percent(part: int, total: int) -> str:
    return "%.1f%%" % ((part / total * 100) if total else 0.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="PDF files or directories")
    parser.add_argument("--data-dir", default=str(ROOT / "data"))
    parser.add_argument("--report", default=str(ROOT / "docs" / "PDF-COVERAGE.md"))
    parser.add_argument("--json", default=str(ROOT / "build" / "pdf-coverage.json"))
    parser.add_argument("--max-files", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS_DEFAULT)
    parser.add_argument("--top", type=int, default=100)
    args = parser.parse_args()

    paths = [Path(value).expanduser().resolve() for value in args.paths]
    pdfs = collect_inputs(paths)
    if not pdfs:
        print("error: no PDFs or word lists found", file=sys.stderr)
        return 1
    pdfs = pdfs[: args.max_files]

    documents: List[Dict] = []
    total_counter: Counter = Counter()
    total_tokens = 0
    pages_read = 0
    skipped: List[Dict] = []

    for path in pdfs:
        try:
            text, pages, kind = extract_input(path, args.max_pages)
        except Exception as error:  # noqa: BLE001 - report per file
            skipped.append({"name": path.name, "error": str(error)})
            continue
        tokens = Counter(TOKEN_RE.findall(text))
        count = sum(tokens.values())
        if count == 0:
            skipped.append(
                {
                    "name": path.name,
                    "error": "no extractable text (scanned or encrypted PDF?)",
                }
            )
            continue
        total_counter.update(tokens)
        total_tokens += count
        pages_read += pages
        documents.append(
            {
                "name": path.name,
                "kind": kind,
                "pages": pages,
                "tokens": count,
                "unique": len(tokens),
                "counter": tokens,
            }
        )
        if total_tokens >= args.max_tokens:
            break

    if not documents:
        print("error: no text could be extracted", file=sys.stderr)
        return 1

    keys = {key_of(token) for token in total_counter}
    headwords, forms, missing = load_dictionary(Path(args.data_dir).resolve(), keys)
    data_meta = json.loads(
        (Path(args.data_dir).resolve() / "meta.json").read_text(encoding="utf-8")
    )
    measured_date = str(data_meta.get("generated_at") or "")[:10] or "unknown"

    category_counts = Counter()
    category_unique = Counter()
    unknown_counter: Counter = Counter()
    missing_counter: Counter = Counter()
    missing_form_counter: Counter = Counter()
    foreign_counter: Counter = Counter()
    form_targets: Dict[str, str] = {}

    for token, count in total_counter.items():
        category, target = classify(token, headwords, forms, missing)
        category_counts[category] += count
        category_unique[category] += 1
        if category == "unknown":
            unknown_counter[token] += count
        elif category == "missing_lemma":
            missing_counter[token] += count
        elif category == "missing_form":
            missing_form_counter[token] += count
            form_targets[token] = target or ""
        elif category == "foreign":
            foreign_counter[token] += count

    per_document = []
    for document in documents:
        doc_counts = Counter()
        doc_unknown = Counter()
        for token, count in document["counter"].items():
            category, target = classify(token, headwords, forms, missing)
            doc_counts[category] += count
            if category == "unknown":
                doc_unknown[token] += count
        known = (
            doc_counts["headword"]
            + doc_counts["form"]
            + doc_counts["missing_lemma"]
            + doc_counts["missing_form"]
        )
        foreign = doc_counts["foreign"]
        portuguese = doc_counts["headword"] + doc_counts["form"] + doc_counts["missing_lemma"] + doc_counts["missing_form"] + doc_counts["unknown"]
        per_document.append(
            {
                "name": document["name"],
                "kind": document["kind"],
                "pages": document["pages"],
                "tokens": document["tokens"],
                "portuguese": portuguese,
                "foreign": foreign,
                "unique": document["unique"],
                "known": known,
                "unknown_unique": len(doc_unknown),
                "counts": dict(doc_counts),
                "top_unknown": doc_unknown.most_common(20),
            }
        )

    known_tokens = (
        category_counts["headword"]
        + category_counts["form"]
        + category_counts["missing_lemma"]
        + category_counts["missing_form"]
    )
    known_unique = (
        category_unique["headword"]
        + category_unique["form"]
        + category_unique["missing_lemma"]
        + category_unique["missing_form"]
    )
    foreign_tokens = category_counts["foreign"]
    portuguese_tokens = total_tokens - foreign_tokens
    portuguese_unique = len(total_counter) - category_unique["foreign"]
    unknown_tokens = category_counts["unknown"]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": [
            {
                "name": item["name"],
                "kind": item["kind"],
                "pages": item["pages"],
                "tokens": item["tokens"],
                "portuguese": item["portuguese"],
                "foreign": item["foreign"],
                "unique": item["unique"],
                "known": item["known"],
                "unknown_unique": item["unknown_unique"],
                "counts": item["counts"],
                "top_unknown": item["top_unknown"],
            }
            for item in per_document
        ],
        "skipped": skipped,
        "data": {
            "headwords": data_meta.get("headwords", 0),
            "missing_lemmas": data_meta.get("missing_lemmas", 0),
            "editorial_definitions": data_meta.get("editorial_definitions", 0),
            "generated_at": data_meta.get("generated_at"),
        },
        "totals": {
            "documents": len(documents),
            "pages": pages_read,
            "tokens": total_tokens,
            "foreign_tokens": foreign_tokens,
            "portuguese_tokens": portuguese_tokens,
            "unique_tokens": len(total_counter),
            "portuguese_unique": portuguese_unique,
            "known_tokens": known_tokens,
            "known_unique": known_unique,
            "unknown_tokens": unknown_tokens,
            "category_counts": dict(category_counts),
            "category_unique": dict(category_unique),
        },
        "top_unknown": unknown_counter.most_common(args.top),
        "top_missing_lemmas": missing_counter.most_common(args.top),
        "top_missing_forms": [
            (token, count, form_targets.get(token, ""))
            for token, count in missing_form_counter.most_common(args.top)
        ],
    }

    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    document_lines = []
    for item in per_document:
        known = item["known"]
        document_lines.append(
            "| `%s` | %s | %s | %s | %s | %s | %s |"
            % (
                item["name"],
                item["pages"],
                f"{item['tokens']:,}",
                f"{item['portuguese']:,}",
                f"{item['foreign']:,}",
                percent(known, item["portuguese"]),
                item["unknown_unique"],
            )
        )

    category_lines = []
    labels = {
        "headword": "Dictionary headword",
        "form": "Resolved by form index",
        "missing_lemma": "Missing-lemma list (exact)",
        "missing_form": "Form of a missing lemma",
        "foreign": "Foreign / function word",
        "unknown": "Unknown",
    }
    for key in (
        "headword",
        "form",
        "missing_lemma",
        "missing_form",
        "foreign",
        "unknown",
    ):
        category_lines.append(
            "| %s | %s | %s |"
            % (
                labels[key],
                f"{category_counts[key]:,}",
                f"{category_unique[key]:,}",
            )
        )

    unknown_lines = []
    for token, count in unknown_counter.most_common(80):
        unknown_lines.append(
            "- `%s` — %s occurrence%s%s"
            % (
                token,
                f"{count:,}",
                "" if count == 1 else "s",
                " (capitalised)" if token[:1].isupper() else "",
            )
        )

    missing_lines = []
    for token, count in missing_counter.most_common(80):
        info = missing.get(fold(token), {})
        missing_lines.append(
            "- `%s` — %s occurrence%s; %s; priority M%s%s"
            % (
                token,
                f"{count:,}",
                "" if count == 1 else "s",
                ", ".join(info.get("pos") or ["unknown"]),
                info.get("priority", "?"),
                ("; near `%s`" % info["near"]) if info.get("near") else "",
            )
        )

    missing_form_lines = []
    for token, count, target in payload["top_missing_forms"][:40]:
        missing_form_lines.append(
            "- `%s` → `%s` — %s occurrence%s"
            % (token, target, f"{count:,}", "" if count == 1 else "s")
        )

    skipped_lines = [
        "- `%s` — %s" % (item["name"], item["error"]) for item in skipped
    ]

    report = """# Lexi2 coverage check

Generated by `scripts/pdf_coverage.py`. The report contains aggregate counts and
token lists, not document text. The PDFs and word lists are external evidence,
not dictionary sources; the dictionary was not modified from them.

The selection is the sample supplied on the command line, not automatically a
representative Portuguese corpus. Judge the coverage in light of that sample.

Measured against runtime data with %s headwords, %s missing lemmas and %s
approved editorial definitions (data generated %s). Re-run the tool after a
data rebuild to refresh these numbers.

## Totals

| Measure | Value |
| --- | ---: |
| Files read | %s |
| PDF pages read | %s |
| Tokens | %s |
| Foreign / function-word tokens | %s |
| Portuguese tokens | %s |
| Unique tokens | %s |
| Portuguese unique tokens | %s |
| Known tokens | %s (%s of Portuguese tokens) |
| Known unique tokens | %s (%s of Portuguese unique tokens) |
| Unknown Portuguese tokens | %s |

## Token classification

| Category | Occurrences | Unique tokens |
| --- | ---: | ---: |
%s

## Per-document coverage

| Document | Pages | Tokens | PT tokens | Foreign | Known (PT) | Unknown unique |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
%s

## Top unknown tokens

Unknown tokens are not necessarily missing dictionary lemmas: they may be proper
nouns, foreign words, OCR errors, abbreviations or inflected forms that the form
index did not resolve.

%s

## Top missing-list lemmas found in the PDFs

These tokens match the lemma-only missing list exactly. They are good candidates
for definition work.

%s

## Top forms of missing lemmas

These tokens resolved through the form index to a missing lemma. They confirm
that the missing list affects real running text.

%s

## Skipped files

%s

## Limits

- Text extraction depends on the PDF's embedded text layer. Scanned PDFs without
  OCR produce little or no text.
- Proper nouns, foreign terms, OCR errors and unhandled inflections remain
  unknown unless the form index resolves them.
- The PDFs were not used to generate or alter the dictionary. Coverage is a
  diagnostic, not a lexicographic review.
""" % (
        f"{data_meta.get('headwords', 0):,}",
        f"{data_meta.get('missing_lemmas', 0):,}",
        f"{data_meta.get('editorial_definitions', 0):,}",
        measured_date,
        f"{len(documents):,}",
        f"{pages_read:,}",
        f"{total_tokens:,}",
        f"{foreign_tokens:,}",
        f"{portuguese_tokens:,}",
        f"{len(total_counter):,}",
        f"{portuguese_unique:,}",
        f"{known_tokens:,}",
        percent(known_tokens, portuguese_tokens),
        f"{known_unique:,}",
        percent(known_unique, portuguese_unique),
        f"{unknown_tokens:,}",
        "\n".join(category_lines),
        "\n".join(document_lines),
        "\n".join(unknown_lines) or "- none",
        "\n".join(missing_lines) or "- none",
        "\n".join(missing_form_lines) or "- none",
        "\n".join(skipped_lines) or "- none",
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print("Files: %s; PDF pages: %s; tokens: %s; Portuguese tokens: %s; known: %s"
          % (
              f"{len(documents):,}",
              f"{pages_read:,}",
              f"{total_tokens:,}",
              f"{portuguese_tokens:,}",
              percent(known_tokens, portuguese_tokens),
          ))
    print("Foreign/function-word tokens: %s; unknown unique: %s; "
          "missing-list exact: %s; missing forms: %s"
          % (
              f"{foreign_tokens:,}",
              f"{len(unknown_counter):,}",
              f"{len(missing_counter):,}",
              f"{len(missing_form_counter):,}",
          ))
    print("Report: %s" % report_path)
    print("JSON:   %s" % json_path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("error: %s" % error, file=sys.stderr)
        raise
