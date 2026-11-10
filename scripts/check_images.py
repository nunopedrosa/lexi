#!/usr/bin/env python3
"""Validate the local illustration set and write the credit pages.

The manifest at ``images/manifest.json`` is the single source of truth for the
pilot illustrations. This script checks that every listed file exists, matches
its recorded SHA-256, size and pixel dimensions, carries an accepted licence
(public domain, CC0 or CC BY) and points at an allowed source. It also verifies
that each illustrated lemma is a real dictionary headword.

With ``--write`` it regenerates ``docs/IMAGES.md`` and ``credits.html`` so the
credit text always matches the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "images" / "manifest.json"
DATA = ROOT / "data"
MAX_BYTES = 260 * 1024
MAX_EDGE = 700
RESIZE_EDGE = 640
ALLOWED_HOSTS = ("commons.wikimedia.org", "www.metmuseum.org")
LICENCE_RE = re.compile(r"^CC BY (\d\.\d)$")


def jpeg_size(path: Path) -> Optional[Tuple[int, int]]:
    """Return (width, height) from a JPEG file, or None."""
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9):
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        i += 2 + length
    return None


def load_headwords() -> set:
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    words = set()
    for key in meta["keys"]:
        path = DATA / ("%s.json" % key)
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8")):
            words.add(row[0])
    return words


def licence_ok(record: Dict) -> Tuple[bool, str]:
    licence = str(record.get("licence") or "")
    if "NC" in licence or "ND" in licence or "SA" in licence:
        return False, "licence %r is not accepted" % licence
    if licence.lower().startswith("cc0") or licence.lower() == "public domain":
        return True, ""
    match = LICENCE_RE.match(licence)
    if not match:
        return False, "licence %r is not recognised" % licence
    if not record.get("licence_url"):
        return False, "CC BY image has no licence URL"
    return True, ""


def check(manifest: Dict, headwords: set) -> List[str]:
    errors: List[str] = []
    seen_files = set()
    seen_lemmas = set()
    total = 0
    for index, record in enumerate(manifest.get("images", []), 1):
        label = "image %d (%s)" % (index, record.get("file") or "?")
        for field in ("file", "lemma", "author", "licence", "source", "retrieved", "sha256"):
            if not record.get(field):
                errors.append("%s: missing %s" % (label, field))
        for field in ("caption", "alt"):
            value = record.get(field) or {}
            if not value.get("pt-PT") or not value.get("en"):
                errors.append("%s: %s needs pt-PT and en text" % (label, field))

        file_name = record.get("file") or ""
        if file_name in seen_files:
            errors.append("%s: duplicate file" % label)
        seen_files.add(file_name)
        lemma = record.get("lemma") or ""
        if lemma in seen_lemmas:
            errors.append("%s: duplicate lemma %r" % (label, lemma))
        seen_lemmas.add(lemma)
        if lemma not in headwords:
            errors.append("%s: lemma %r is not a dictionary headword" % (label, lemma))

        path = ROOT / "images" / file_name
        if not path.exists():
            errors.append("%s: file does not exist" % label)
            continue
        data = path.read_bytes()
        total += len(data)
        if len(data) > MAX_BYTES:
            errors.append("%s: %s bytes exceeds %s" % (label, len(data), MAX_BYTES))
        if hashlib.sha256(data).hexdigest() != record.get("sha256"):
            errors.append("%s: SHA-256 mismatch" % label)
        if len(data) != record.get("bytes"):
            errors.append("%s: byte count mismatch" % label)
        size = jpeg_size(path)
        if size is None:
            errors.append("%s: not a readable JPEG" % label)
        else:
            width, height = size
            if (width, height) != (record.get("width"), record.get("height")):
                errors.append("%s: dimension mismatch (%sx%s)" % (label, width, height))
            if max(width, height) > MAX_EDGE:
                errors.append("%s: %sx%s exceeds %s px" % (label, width, height, MAX_EDGE))

        ok, reason = licence_ok(record)
        if not ok:
            errors.append("%s: %s" % (label, reason))
        source = record.get("source") or ""
        host = re.sub(r"^https?://", "", source).split("/")[0].lower()
        if host and host not in ALLOWED_HOSTS:
            errors.append("%s: source host %r is not allowed" % (label, host))

    declared = manifest.get("bytes")
    if declared != total:
        errors.append("manifest bytes %r does not match file total %r" % (declared, total))
    return errors


def licence_text(record: Dict) -> Tuple[str, str]:
    licence = record["licence"]
    url = record.get("licence_url") or ""
    if url:
        return "", ' <a href="%s" rel="noopener noreferrer">%s</a>' % (
            html.escape(url, quote=True),
            html.escape(licence),
        )
    return html.escape(licence), ""


def write_docs(manifest: Dict) -> None:
    lines = [
        "# Illustration credits",
        "",
        "Generated by `scripts/check_images.py --write` from `images/manifest.json`.",
        "Each image is a local copy; the source page and licence are recorded for",
        "credit and verification. Images keep their own licence and are not part of",
        "the GPL-3.0 code or the dictionary database.",
        "",
        "| Lemma | File | Caption (pt-PT) | Author | Licence | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in manifest["images"]:
        caption = record["caption"]["pt-PT"]
        licence = record["licence"]
        if record.get("licence_url"):
            licence = "[%s](%s)" % (licence, record["licence_url"])
        lines.append(
            "| `%s` | `%s` | %s | %s | %s | [source](%s) |"
            % (
                record["lemma"],
                record["file"],
                caption,
                record["author"],
                licence,
                record["source"],
            )
        )
    lines.extend(
        [
            "",
            "All files were resized to a maximum of %d px and re-encoded as JPEG."
            % RESIZE_EDGE,
            "",
        ]
    )
    (ROOT / "docs" / "IMAGES.md").write_text("\n".join(lines), encoding="utf-8")

    rows = []
    for record in manifest["images"]:
        licence_label, licence_html = licence_text(record)
        origin_html = ' · <a href="%s" rel="noopener noreferrer">origem / source</a>' % html.escape(
            record["source"], quote=True
        )
        rows.append(
            '  <li><strong>%s</strong> — %s / %s. %s. %s%s%s</li>'
            % (
                html.escape(record["lemma"]),
                html.escape(record["caption"]["pt-PT"]),
                html.escape(record["caption"]["en"]),
                html.escape(record["author"]),
                licence_label,
                licence_html,
                origin_html,
            )
        )
    page = """<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#153d52">
<link rel="stylesheet" href="style.css">
<title>Lexi — Créditos das ilustrações / Illustration credits</title>
</head>
<body class="missing-page">
<header>
 <div class="brand">
  <img class="brand-mark" src="icons/mark.svg" alt="" width="40" height="40">
  <div class="brand-text">
   <strong>Lexi</strong>
   <small>Créditos das ilustrações · Illustration credits</small>
  </div>
 </div>
 <div class="header-actions">
  <a class="back-link" href="./">Voltar à Lexi · Back to Lexi</a>
 </div>
</header>
<main>
 <h1>Créditos das ilustrações · Illustration credits</h1>
 <p class="helper">As ilustrações são cópias locais de ficheiros de acesso livre. Cada uma mantém a sua própria licença e é creditada ao autor. Não fazem parte do código GPL-3.0 nem da base do dicionário.<br>The illustrations are local copies of openly licensed files. Each keeps its own licence and is credited to its author. They are not part of the GPL-3.0 code or the dictionary database.</p>
 <ul class="credits-list">
%s
 </ul>
 <p class="helper">Todas as imagens foram redimensionadas para um máximo de %d px e recodificadas em JPEG.</p>
</main>
</body>
</html>
""" % ("\n".join(rows), RESIZE_EDGE)
    (ROOT / "credits.html").write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate docs/IMAGES.md and credits.html")
    parser.add_argument("--manifest", default=str(MANIFEST))
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        print("error: unsupported manifest schema", file=sys.stderr)
        return 1
    headwords = load_headwords()
    errors = check(manifest, headwords)
    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        return 1
    if args.write:
        write_docs(manifest)
    print(
        "Illustrations OK: %d files, %s bytes, %s lemmas"
        % (
            len(manifest["images"]),
            f"{manifest['bytes']:,}",
            len({record["lemma"] for record in manifest["images"]}),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
