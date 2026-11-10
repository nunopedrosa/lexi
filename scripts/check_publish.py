#!/usr/bin/env python3
"""Check that the publication profile can serve the app shell.

The BaseCentral deploy engine copies only the paths named by
``scripts/deploy-profile.sh``. If ``sw.js`` precaches a file that is not
published, ``cache.addAll`` rejects the whole install: no service worker is
installed, updates cannot be detected, and the site silently keeps serving an
old shell (or none). The same happens for the credits page and every
illustration referenced by ``images/manifest.json``.

This check reads the service-worker precache list and the publication
allowlist, expands the illustration glob and fails if:

* a published path does not exist;
* a precached path is not published;
* an illustration is missing from the publication list;
* an ``images/*.jpg`` file is not referenced by the manifest (unreviewed files
  must not be published).

Run it directly or let ``deploy_validate`` in the profile run it before
staging.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Set

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def public_files(root: Path) -> List[str]:
    text = read_text(root / "scripts" / "deploy-profile.sh")
    match = re.search(
        r"^PUBLIC_FILES=\$\(cat <<'PUBLIC_FILES'\n(.*?)^PUBLIC_FILES$",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise SystemExit("deploy-profile.sh: PUBLIC_FILES block not found")
    files = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    if "images/*.jpg" in text:
        files.extend("images/%s" % path.name for path in sorted((root / "images").glob("*.jpg")))
    return files


def supplied_files(source: str) -> List[str]:
    stream = sys.stdin if source == "-" else open(source, encoding="utf-8")
    try:
        return [line.strip() for line in stream if line.strip()]
    finally:
        if source != "-":
            stream.close()


def core_files(root: Path) -> List[str]:
    text = read_text(root / "sw.js")
    match = re.search(r"^const CORE=\[(.*?)^\];", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise SystemExit("sw.js: CORE precache list not found")
    return re.findall(r"'([^']+)'", match.group(1))


def normalise(relative: str) -> str:
    return relative[2:] if relative.startswith("./") else relative


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=str(DEFAULT_ROOT))
    parser.add_argument(
        "--files",
        help="check this publication list instead of the profile (use - for stdin)",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()

    published_list = supplied_files(args.files) if args.files else public_files(root)
    if not published_list:
        print("error: empty publication allowlist", file=sys.stderr)
        return 1
    published: Set[str] = set()
    errors: List[str] = []

    for relative in published_list:
        if relative in published:
            errors.append("duplicate public path: %s" % relative)
            continue
        published.add(relative)
        if not (root / relative).is_file():
            errors.append("public path does not exist: %s" % relative)

    core = core_files(root)
    for relative in core:
        relative = normalise(relative)
        if not relative:
            continue
        if not (root / relative).is_file():
            errors.append("sw.js precaches a missing file: %s" % relative)
        if relative not in published:
            errors.append("sw.js precaches an unpublished file: %s" % relative)

    manifest = json.loads(read_text(root / "images" / "manifest.json"))
    referenced = set()
    for record in manifest.get("images", []):
        file_name = record.get("file")
        if not file_name:
            continue
        relative = "images/%s" % file_name
        referenced.add(relative)
        if relative not in published:
            errors.append("illustration is not published: %s" % relative)
        elif not (root / relative).is_file():
            errors.append("illustration is missing: %s" % relative)

    on_disk = {"images/%s" % path.name for path in (root / "images").glob("*.jpg")}
    for relative in sorted(on_disk - referenced):
        errors.append("image is not listed in the manifest: %s" % relative)

    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        return 1
    print(
        "Publication OK: %d public files, %d precached assets, %d illustrations"
        % (len(published), len(core), len(referenced))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
