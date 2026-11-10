#!/usr/bin/env python3
"""Apply image replacement tags exported from the Lexi2 app (development tool).

The app lets the user tag an illustration for replacement ("wrong image",
"could be better", "remove"). Tags stay on the device and leave it only inside
a backup file (`imageTags` section, next to `personalDefinitions`). This
script reads that backup and makes the tags permanent in the repository:

  remove            -> the illustration is removed from images/manifest.json
                       (the file is deleted unless --keep-files).
  wrong / better    -> the image is replaced, from the first source available:
                         1. the tag's own replacement URL (a Wikimedia Commons
                            file page recorded in the app);
                         2. --choose lemma=N: candidate #N from the stored
                            fetch record in .work/illustrations-auto/records;
                         3. --refetch: search Commons again for the lemma
                            (or the tag's note text with --query-from-note).
                       Without any replacement source the tag is reported as
                       pending and left in place.
  wanted            -> the reader asked for an illustration where none is
                       bundled. The tag's note is the sense-specific search
                       description and its URL is the Google Images search that
                       was opened. With --refetch the script searches Commons
                       and prints candidates for human review. It does not add
                       a manifest entry automatically: captions, alt text and
                       licence acceptance are still editorial decisions.
                       Without --refetch the request is reported as pending.

After applying, credits.html and docs/IMAGES.md are regenerated through
scripts/check_images.py and the release identifier in version.js is bumped
unless --no-bump. Nothing is uploaded anywhere; this is a local build step.

Examples:
  python3 scripts/apply_image_tags.py --backup-file lexi2-backup.json --dry-run
  python3 scripts/apply_image_tags.py --backup-file lexi2-backup.json
  python3 scripts/apply_image_tags.py --backup-file b.json --refetch --auto
  python3 scripts/apply_image_tags.py --backup-file b.json --choose aboboreira=2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_illustrations as fi  # noqa: E402

IMAGES = ROOT / "images"
MANIFEST = IMAGES / "manifest.json"
VERSION_JS = ROOT / "version.js"
WORK_RECORDS = ROOT / ".work" / "illustrations-auto" / "records"
WORK_IMAGES = ROOT / ".work" / "illustrations-auto" / "images"

UA = "lexi2-image-tag-apply/1.0"


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def http_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def load_backup(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != "lexi2-backup":
        raise SystemExit("not a Lexi2 backup file: %s" % path)
    tags = data.get("imageTags")
    if not isinstance(tags, list):
        raise SystemExit("backup has no imageTags section (export a newer backup)")
    out = []
    for item in tags:
        if not isinstance(item, dict):
            continue
        lemma = (item.get("lemma") or "").strip()
        action = (item.get("action") or "").strip()
        if not lemma or action not in ("wrong", "better", "remove", "wanted"):
            continue
        out.append({
            "lemma": lemma,
            "action": action,
            "note": (item.get("note") or "").strip()[:300],
            "url": (item.get("url") or "").strip(),
            "tagged": (item.get("tagged") or "").strip(),
        })
    return out


def commons_info_from_page_url(url):
    """Resolve a commons.wikimedia.org/wiki/File: page URL to image info."""
    m = re.match(r"^https://commons\.wikimedia\.org/wiki/File:(.+)$", url, re.I)
    if not m:
        return None
    title = "File:" + urllib.parse.unquote(m.group(1).replace("_", " "))
    params = {
        "action": "query", "format": "json", "titles": title,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": "960",
        "iiextmetadatafilter": "LicenseShortName|Artist|Credit",
    }
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = http_json(api)
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        if page.get("title", "").lower() != title.lower():
            continue
        ii = (page.get("imageinfo") or [None])[0]
        if not ii:
            return None
        em = ii.get("extmetadata") or {}
        def val(k):
            return re.sub(r"<[^>]*>", "", em.get(k, {}).get("value", "")).strip()
        return {
            "title": page.get("title", ""),
            "licence": val("LicenseShortName"),
            "artist": val("Artist")[:120] or "Unknown",
            "url": ii.get("thumburl") or ii.get("url", ""),
            "source": ii.get("descriptionurl", url),
        }
    return None


def fetch_replacement_image(info, dest):
    blob = http_bytes(info["url"])
    dest.write_bytes(blob)
    if not fi.resize_to_jpeg(dest, dest):
        raise SystemExit("could not resize replacement for %s" % info["title"])
    size = fi.jpeg_size(dest)
    data = dest.read_bytes()
    if not size or max(size) > fi.MAX_EDGE:
        raise SystemExit("bad dimensions for %s" % info["title"])
    if len(data) > fi.MAX_BYTES:
        raise SystemExit("file too large for %s (%d bytes)" % (info["title"], len(data)))
    return {
        "data": data,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "width": size[0],
        "height": size[1],
    }


def record_for(lemma):
    stem = fi.file_stem(lemma)
    path = WORK_RECORDS / (stem + ".json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def refetch_candidates(lemma, query):
    params = {
        "action": "query", "format": "json",
        "generator": "search",
        "gsrsearch": "filetype:bitmap " + query,
        "gsrnamespace": "6", "gsrlimit": "20",
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": "960",
        "iiextmetadatafilter": "LicenseShortName|Artist|Credit",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = http_json(url)
    out = []
    for page in (data.get("query") or {}).get("pages", {}).values():
        ii = (page.get("imageinfo") or [None])[0]
        if not ii:
            continue
        em = ii.get("extmetadata") or {}
        def val(k):
            return re.sub(r"<[^>]*>", "", em.get(k, {}).get("value", "")).strip()
        out.append({
            "title": page.get("title", ""),
            "licence": val("LicenseShortName"),
            "artist": val("Artist")[:120],
            "width": ii.get("width", 0),
            "height": ii.get("height", 0),
            "mime": ii.get("mime", ""),
            "thumburl": ii.get("thumburl") or ii.get("url", ""),
            "source": ii.get("descriptionurl", ""),
        })
    scored = []
    for cand in out:
        s = fi.score_candidate(cand, lemma)
        if s is not None:
            scored.append((s, cand))
    scored.sort(key=lambda sc: -sc[0])
    return [c for s, c in scored]


def replace_manifest_entry(manifest, lemma, info, img, today):
    for entry in manifest["images"]:
        if entry["lemma"] != lemma:
            continue
        entry["author"] = info.get("artist") or "Unknown"
        entry["licence"] = info["licence"]
        entry["licence_url"] = fi.licence_url(info["licence"])
        entry["source"] = info.get("source") or entry.get("source", "")
        entry["retrieved"] = today
        entry["modified"] = "Replaced by a user tag; resized to 640 px and re-encoded as JPEG (quality 78)."
        entry["sha256"] = img["sha256"]
        entry["bytes"] = img["bytes"]
        entry["width"] = img["width"]
        entry["height"] = img["height"]
        return entry
    return None


def write_manifest(manifest):
    manifest["bytes"] = sum(r["bytes"] for r in manifest["images"])
    manifest["generated"] = time.strftime("%Y-%m-%d")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")


def bump_version():
    text = VERSION_JS.read_text(encoding="utf-8")
    m = re.search(r"LEXI_VERSION='(\d{4})\.(\d{2})\.(\d{2})\.(\d+)'", text)
    if not m:
        print("warning: could not parse LEXI_VERSION; not bumped")
        return
    next_rev = int(m.group(4)) + 1
    replacement = "LEXI_VERSION='%s.%s.%s.%d'" % (m.group(1), m.group(2), m.group(3), next_rev)
    VERSION_JS.write_text(text.replace(m.group(0), replacement), encoding="utf-8")
    print("bumped LEXI_VERSION -> %s.%s.%s.%d" % (m.group(1), m.group(2), m.group(3), next_rev))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backup-file", required=True, help="exported Lexi2 backup JSON")
    ap.add_argument("--choose", action="append", default=[],
                    metavar="LEMMA=N", help="use candidate #N from the stored fetch record")
    ap.add_argument("--refetch", action="store_true",
                    help="re-search Commons for lemmas without URL/choose")
    ap.add_argument("--query-from-note", action="store_true",
                    help="with --refetch: search using the tag note instead of the lemma")
    ap.add_argument("--auto", action="store_true",
                    help="with --refetch: accept the best-scoring candidate without asking")
    ap.add_argument("--keep-files", action="store_true",
                    help="do not delete image files of removed illustrations")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-bump", action="store_true", help="do not bump version.js")
    ap.add_argument("--contact", default=None, help="contact for the User-Agent")
    args = ap.parse_args()
    if args.contact:
        global UA
        UA = "%s (%s)" % (UA, args.contact)

    tags = load_backup(args.backup_file)
    if not tags:
        print("no usable tags in backup")
        return 0
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_lemma = {r["lemma"]: r for r in manifest["images"]}
    choose = {}
    for item in args.choose:
        lemma, _, n = item.partition("=")
        choose[lemma.strip()] = int(n)

    today = time.strftime("%Y-%m-%d")
    changed = False
    pending = 0
    for tag in tags:
        lemma = tag["lemma"]
        entry = by_lemma.get(lemma)
        if tag["action"] == "wanted":
            query = tag["note"] or lemma
            print("wanted  %-16s %s" % (lemma, query[:60]))
            if entry:
                print("  -> already illustrated; request satisfied")
                continue
            if args.refetch:
                cands = refetch_candidates(lemma, query)
                if not cands:
                    print("  -> no acceptable Commons candidate for this query")
                else:
                    print("  candidates for %s (review before adding; captions "
                          "are not automatic):" % lemma)
                    for i, c in enumerate(cands[:8], 1):
                        print("    %d. %s | %s" % (i, c["title"][:70], c["licence"]))
            else:
                print("  -> pending: open Google Images or rerun with --refetch")
            pending += 1
            continue
        if not entry:
            print("skip    %-16s not illustrated (already removed?)" % lemma)
            continue
        print("tag     %-16s %-6s %s" % (lemma, tag["action"],
              (tag["note"] or "")[:60]))
        if tag["action"] == "remove":
            print("  -> would remove %s" % entry["file"])
            if not args.dry_run:
                manifest["images"].remove(entry)
                del by_lemma[lemma]
                path = IMAGES / entry["file"]
                if path.exists() and not args.keep_files:
                    path.unlink()
            changed = True
            continue
        # wrong / better: need a replacement
        info = None
        source = None
        if tag["url"]:
            info = commons_info_from_page_url(tag["url"])
            if info is None:
                print("  -> URL did not resolve to a Commons file: %s" % tag["url"])
            elif not fi.LICENCE_RE.match(info["licence"]):
                print("  -> URL licence not accepted: %s" % info["licence"])
                info = None
            else:
                source = "url"
        if info is None and lemma in choose:
            rec = record_for(lemma)
            cands = (rec or {}).get("candidates") or []
            n = choose[lemma]
            if not (1 <= n <= len(cands)):
                print("  -> --choose %s=%d out of range (1-%d)" % (lemma, n, len(cands)))
            else:
                cand = cands[n - 1]
                info = {"title": cand["title"], "licence": cand["licence"],
                        "artist": cand.get("artist") or "Unknown",
                        "url": cand["thumburl"], "source": cand.get("source", "")}
                source = "candidate #%d" % n
                if not fi.LICENCE_RE.match(info["licence"]):
                    print("  -> candidate licence not accepted: %s" % info["licence"])
                    info = None
        if info is None and args.refetch:
            query = lemma
            if args.query_from_note and tag["note"]:
                query = tag["note"][:80]
            cands = refetch_candidates(lemma, query)
            if not cands:
                print("  -> refetch found no acceptable candidate")
            else:
                if args.auto:
                    pick, which = cands[0], "#1 (auto)"
                else:
                    print("  candidates for %s:" % lemma)
                    for i, c in enumerate(cands[:8], 1):
                        print("    %d. %s | %s" % (i, c["title"][:70], c["licence"]))
                    pick, which = None, ""
                if pick is not None:
                    info = {"title": pick["title"], "licence": pick["licence"],
                            "artist": pick.get("artist") or "Unknown",
                            "url": pick["thumburl"], "source": pick["source"]}
                    source = "refetch %s" % which
                    if not fi.LICENCE_RE.match(info["licence"]):
                        print("  -> refetch licence not accepted: %s" % info["licence"])
                        info = None
        if info is None:
            pending += 1
            print("  -> pending: no replacement source (use the app URL field, "
                  "--choose or --refetch)")
            continue
        print("  -> would replace from %s: %s | %s" % (source, info["title"][:60], info["licence"]))
        if not args.dry_run:
            stem = fi.file_stem(lemma)
            dest = IMAGES / (stem + ".jpg")
            img = fetch_replacement_image(info, dest)
            if not replace_manifest_entry(manifest, lemma, info, img, today):
                print("  -> entry vanished during apply; skipped")
                continue
            changed = True
    if args.dry_run:
        print("dry run — nothing written; %d tag(s) pending" % pending)
        return 0
    if changed:
        write_manifest(manifest)
        subprocess_check_images()
        if not args.no_bump:
            bump_version()
    applied = len(tags) - pending
    print("applied %d of %d tag(s); %d pending" % (applied, len(tags), pending))
    if pending:
        print("pending tags stay on the device; export again after fixing them")
    return 0


def subprocess_check_images():
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_images.py"), "--write"])
    if r.returncode != 0:
        raise SystemExit("check_images.py failed")


if __name__ == "__main__":
    sys.exit(main())
