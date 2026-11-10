#!/usr/bin/env python3
"""Download, verify and extract the pinned Lexi2 source snapshots.

The snapshots are intentionally pinned by SHA-256. ``latest`` in a URL is only
an upstream convenience; a changed file fails verification until this script and
docs/SOURCES.md are reviewed and updated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / ".work" / "sources"
DEFAULT_BUILD = ROOT / "build"

# The Wiktionary bridge snapshot is the dictionary data compiled in the
# sibling Lexi project (Portuguese and English Wiktionary via kaikki.org,
# wiktextract). It is a local source: the files are copied into
# .work/sources/lexi-wikt/ and pinned per file, so a changed sibling checkout
# fails verification until the pins and docs/SOURCES.md are reviewed.
LEXI_DATA_DIR = ROOT.parent / "lexi" / "data"
LEXI_WIKT_FILES = [
    ("_.json", "f7665614683d8f9a69b9ded03f94b3464d2734f19f93b92e0c49042a2b8ee547"),
    ("a.json", "ec8ce9c37356c69c9bc3b7109f4be651ac890f2989fd8569a3fa3099c6e77a5b"),
    ("b.json", "2a3b1a7ccf412632b2ec4067410bb3c739103cebb33882a9b80deb52bea3d4f2"),
    ("c.json", "75c50875c50d91ba6f11ff99a7350893776cbfe86995dc960ce6ab9d472f55da"),
    ("d.json", "bca6d6080bb3911955e669d1b2529e18a8ea31b79d152050f0a92130b24f4f28"),
    ("e.json", "99581476cc9a2105878fedbdd9b403c7b8dae73967f56f82a3293d55785716e3"),
    ("f.json", "f811553cccab57f82de18b5940fae1e4f1a1fcfbbc53fc68115b3fda1bab6f78"),
    ("g.json", "ad10c43f65e3331fb7b90b840209b1cc385ae73141489964925a435cdfc7f865"),
    ("h.json", "c6ef4bf5ad233927fd1ac2c1ae608e0bcc6fa032d208ae8a43f137de0dbf88b3"),
    ("i.json", "37f4edd7810e443e7a440498063a6c1347ea1f26127bdb70717410cee5770599"),
    ("j.json", "8dabc0f09a26847d0f2718ba58826558c3c863a3a19a52c2f4ef526787282ca7"),
    ("k.json", "2fcbb16a6b9dd163f0369fa52b69c127ea17979c2be7cfe20fb822d38810ebf6"),
    ("l.json", "106208c30ca2ee5470a08a2e3456cd57ac927a8655a92757a010f7fcb485322f"),
    ("m.json", "7b1d075154040e649fcde76445e672253842930f885c853b259d61ccd1061abd"),
    ("n.json", "a588075a3ca002b7009ca56cb7b32cd3f49abfbb7ded024a79e914d273bbb43e"),
    ("o.json", "4fd5165a106770f034e211778239f470753c2be2f1284fa6225bc16df4606412"),
    ("p.json", "e352297c9ee3ac57e329355021039eb7bc2ea6c68726b36915f0d437667639e9"),
    ("q.json", "11630bf60aab4e97e9008944c2e90c746349c1884de07662b07ade2439589130"),
    ("r.json", "907d32c1d9a3cbd3fc88b49f0a0065a81d0c9317bf5bbb63728cac52e0f50eda"),
    ("s.json", "df08e8177776468acff97bb53964d0d1238233f3b209bf2a233ffc2d031d5d48"),
    ("t.json", "00283ab7e5514f1107b6a45639f3dd28caf7880e74c6e93c8ebf29f6d64f0b08"),
    ("u.json", "705a3e1deff37c7dffee56976c8ecf9dd42c0e0854223cea747b3a7157f2fbf4"),
    ("v.json", "bf385cb86b89b41da53032c970639a1a642e93121fc919a462a478ae5ccb4870"),
    ("w.json", "7bdc657be9771ba9830701760ace37e29bf7d97f947b380251f8936340609e70"),
    ("x.json", "ff95868f2a2ac46491aa14b027e5b38b6c161edffe369fe9bd4eea4f1b5aadd7"),
    ("y.json", "f67933f498ac03e87e636f304c867e89b3c7179a2775d5853f34705e5e42c790"),
    ("z.json", "f87169b39741c34d9fa2f68a1e44f3bf67c2723b7aabeeb5b211d14179b470da"),
]
LOCAL_SOURCES: List[Dict[str, object]] = [
    {
        "name": "wikt-pt-lexi",
        "kind": "local-dir",
        "from": str(LEXI_DATA_DIR),
        "target": "lexi-wikt",
        "files": [
            {"name": name, "sha256": digest}
            for name, digest in LEXI_WIKT_FILES
        ],
        "licence": "CC-BY-SA-4.0",
        "snapshot": (
            "sibling Lexi data at commit 900df5d9906e5f6c411bf5a4afb9154e6420ca08 "
            "(2026-11-08); Portuguese and English Wiktionary via kaikki.org "
            "(wiktextract)"
        ),
    },
]

SOURCES: List[Dict[str, str]] = [
    {
        "name": "words-pt",
        "filename": "wordsList.zip",
        "url": "https://raw.githubusercontent.com/jfoclpf/words-pt/master/wordsList.zip",
        "sha256": "8459f51d8e0de19593be43b41a21c64a1026a84132e5410bd320c43fe93d8213",
        "kind": "zip",
        "licence": "GPL-3.0",
        "snapshot": "word list dated 2020-03-02",
    },
    {
        "name": "dicionario-aberto",
        "filename": "data-20151213.sql.xz",
        "url": "https://raw.githubusercontent.com/ambs/Dicionario-Aberto/master/SQL/data-20151213.sql.xz",
        "sha256": "a48a2f36d59815c44adf531b6453f7cc63998e2dfa48d25452d0be33affb6fa9",
        "kind": "xz",
        "output": "da.sql",
        "licence": "CC-BY-SA-2.5-PT",
        "snapshot": "2015-12-13",
    },
    {
        "name": "hunspell-pt-PT",
        "filename": "hunspell-pt_PT-latest.tar.gz",
        "url": "https://natura.di.uminho.pt/download/sources/Dictionaries/hunspell/LATEST/hunspell-pt_PT-latest.tar.gz",
        "sha256": "2066157087e83264484a6d564e1d85258fe2c5eddb9713a42d6f6cf06b0a2ed9",
        "kind": "tar",
        "licence": "GPL/LGPL/MPL",
        "snapshot": "2025-10-01",
    },
    {
        "name": "natura-wordlist-ao",
        "filename": "wordlist-ao-latest.txt.xz",
        "url": "https://natura.di.uminho.pt/download/sources/Dictionaries/wordlists/LATEST/wordlist-ao-latest.txt.xz",
        "sha256": "ac5fb0cd0359d6b4678dc3d93e3311e008367a23f187f893f8b37662dfec0344",
        "kind": "xz",
        "output": "wordlist-ao.txt",
        "licence": "GPL/LGPL/MPL",
        "snapshot": "2025-10-01",
    },
    {
        "name": "natura-wordlist-preao",
        "filename": "wordlist-preao-latest.txt.xz",
        "url": "https://natura.di.uminho.pt/download/sources/Dictionaries/wordlists/LATEST/wordlist-preao-latest.txt.xz",
        "sha256": "aadc31a7c33315be84316f8235ed808f39d01c5a5a05c29e91e2da5a698c9f72",
        "kind": "xz",
        "output": "wordlist-preao.txt",
        "licence": "GPL/LGPL/MPL",
        "snapshot": "2025-10-01",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    print("Downloading %s" % url)
    with urllib.request.urlopen(url, timeout=120) as response:
        with open(temporary, "wb") as handle:
            shutil.copyfileobj(response, handle)
    temporary.replace(destination)


def extract(source: Dict[str, str], sources_dir: Path) -> Path:
    path = sources_dir / source["filename"]
    kind = source["kind"]

    archive_mtime = path.stat().st_mtime

    if kind == "zip":
        output = sources_dir / "wordsList"
        if output.exists() and output.stat().st_mtime >= archive_mtime:
            return output
        with zipfile.ZipFile(path) as archive:
            archive.extractall(sources_dir)
        return output

    if kind == "xz":
        output = sources_dir / source["output"]
        if output.exists() and output.stat().st_mtime >= archive_mtime:
            return output
        with lzma.open(path, "rb") as compressed:
            with open(output, "wb") as handle:
                shutil.copyfileobj(compressed, handle)
        return output

    if kind == "tar":
        candidates = sorted(sources_dir.glob("hunspell-pt_PT-*/pt_PT.dic"))
        if candidates:
            newest = max(candidate.stat().st_mtime for candidate in candidates)
            if newest >= archive_mtime:
                return candidates[-1]
        with tarfile.open(path, "r:gz") as archive:
            archive.extractall(sources_dir)
        candidates = sorted(sources_dir.glob("hunspell-pt_PT-*/pt_PT.dic"))
        if not candidates:
            raise FileNotFoundError("pt_PT.dic not found in Hunspell archive")
        return candidates[-1]

    raise ValueError("Unknown source kind: %s" % kind)


def sync_local_sources(sources_dir: Path) -> None:
    """Copy the pinned local snapshots into the sources directory."""

    for source in LOCAL_SOURCES:
        target = sources_dir / str(source["target"])
        target.mkdir(parents=True, exist_ok=True)
        origin = Path(str(source["from"]))
        files = source["files"]
        for entry in files:
            path = target / str(entry["name"])
            if path.exists():
                continue
            origin_path = origin / str(entry["name"])
            if not origin_path.exists():
                raise FileNotFoundError(
                    "Missing %s; the sibling Lexi checkout is required for the "
                    "Wiktionary bridge snapshot" % origin_path
                )
            shutil.copyfile(origin_path, path)
        print("Copied %s (%d files) from %s" % (target.name, len(files), origin))


def verify_sources(sources_dir: Path, require_extracted: bool = True) -> List[Dict]:
    records = []
    for source in SOURCES:
        path = sources_dir / source["filename"]
        if not path.exists():
            raise FileNotFoundError(
                "Missing %s. Run scripts/fetch_sources.py first." % path
            )
        actual = sha256(path)
        if actual != source["sha256"]:
            raise ValueError(
                "SHA-256 mismatch for %s: expected %s, got %s"
                % (path.name, source["sha256"], actual)
            )
        record = {
            "name": source["name"],
            "filename": source["filename"],
            "url": source["url"],
            "sha256": actual,
            "size": path.stat().st_size,
            "licence": source["licence"],
            "snapshot": source["snapshot"],
        }
        if require_extracted:
            extracted = extract(source, sources_dir)
            record["extracted"] = str(extracted.relative_to(sources_dir))
        records.append(record)

    for source in LOCAL_SOURCES:
        target = sources_dir / str(source["target"])
        verified_files = []
        manifest = hashlib.sha256()
        for entry in source["files"]:
            path = target / str(entry["name"])
            if not path.exists():
                raise FileNotFoundError(
                    "Missing %s. Run scripts/fetch_sources.py first." % path
                )
            actual = sha256(path)
            if actual != entry["sha256"]:
                raise ValueError(
                    "SHA-256 mismatch for %s: expected %s, got %s"
                    % (path, entry["sha256"], actual)
                )
            verified_files.append(
                {
                    "name": entry["name"],
                    "sha256": actual,
                    "size": path.stat().st_size,
                }
            )
            manifest.update(actual.encode("ascii"))
        records.append(
            {
                "name": source["name"],
                "filename": "%s (%d files)" % (source["target"], len(verified_files)),
                "url": str(source["from"]),
                "sha256": manifest.hexdigest(),
                "size": sum(item["size"] for item in verified_files),
                "licence": source["licence"],
                "snapshot": source["snapshot"],
                "files": verified_files,
            }
        )
    return records


def find_hunspell(sources_dir: Path) -> Path:
    candidates = sorted(sources_dir.glob("hunspell-pt_PT-*/pt_PT.dic"))
    if not candidates:
        raise FileNotFoundError("Hunspell pt_PT.dic not found")
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources-dir",
        default=str(DEFAULT_SOURCES),
        help="Directory for downloaded snapshots (default: .work/sources)",
    )
    parser.add_argument(
        "--build-dir",
        default=str(DEFAULT_BUILD),
        help="Directory for build metadata (default: build)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing snapshots without downloading",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download again even when a verified file exists",
    )
    args = parser.parse_args()

    sources_dir = Path(args.sources_dir).resolve()
    build_dir = Path(args.build_dir).resolve()
    sources_dir.mkdir(parents=True, exist_ok=True)

    if not args.check:
        for source in SOURCES:
            path = sources_dir / source["filename"]
            if path.exists() and not args.force:
                actual = sha256(path)
                if actual == source["sha256"]:
                    print("Verified %s" % path.name)
                    continue
                raise ValueError(
                    "Existing %s has the wrong hash. Use --force to replace it."
                    % path.name
                )
            download(source["url"], path)
            actual = sha256(path)
            if actual != source["sha256"]:
                raise ValueError(
                    "Downloaded %s has the wrong hash: %s" % (path.name, actual)
                )
            print("Verified %s" % path.name)
        sync_local_sources(sources_dir)

    records = verify_sources(sources_dir, require_extracted=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_dir": str(sources_dir),
        "sources": records,
    }
    (build_dir / "sources.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\nSnapshots verified:")
    for record in records:
        print(
            "  %-28s %s  %s"
            % (record["name"], record["sha256"][:12], record["licence"])
        )
    print("\nMetadata: %s" % (build_dir / "sources.json"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - command-line tool
        print("error: %s" % error, file=sys.stderr)
        sys.exit(1)
