#!/usr/bin/env python3
"""Fetch illustration candidates from Wikimedia Commons, without an LLM.

The pipeline has four stages; each is a subcommand:

  queue      Build (or rebuild) the candidate lemma queue from the generated
             dictionary shards using concreteness heuristics on the head
             sense. Written to .work/illustrations-auto/queue.json.
  fetch      Fetch candidates for pending queue entries at a slow, polite
             pace. Downloads are verified, downscaled to 640 px JPEG and
             stored in .work/illustrations-auto/ together with a metadata
             record per lemma. Resumable: every run is bounded by --limit
             (or --lemmas) so it can be repeated until the queue is done.
  report     Write .work/illustrations-auto/review.html, a local review page
             showing each candidate with its licence, author, source and the
             dictionary sense, with boxes to approve and write captions.
  integrate  Copy the lemmas selected in a review-selection file into
             images/, append them to images/manifest.json and regenerate
             docs/IMAGES.md and credits.html via scripts/check_images.py.

Nothing reaches images/ or the manifest without an explicit selection file
produced from the review page: automation proposes, a human decides what is
committed (see AGENTS.md). Only public domain, CC0 and CC BY images from
allowed hosts are accepted; NC, ND and SA material is refused.

Requests go to the Commons API and upload servers with a descriptive
User-Agent and conservative delays (see --delay). Large runs should be spread
over multiple invocations; state is kept between runs.

Examples:
  python3 scripts/fetch_illustrations.py queue --category animais
  python3 scripts/fetch_illustrations.py fetch --limit 25
  python3 scripts/fetch_illustrations.py fetch --lemmas pato,burro
  python3 scripts/fetch_illustrations.py report
  python3 scripts/fetch_illustrations.py integrate --selection-file review-selection.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import struct
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WORK = ROOT / ".work" / "illustrations-auto"
IMAGES = ROOT / "images"
MANIFEST = IMAGES / "manifest.json"
QUEUE = WORK / "queue.json"
REVIEW = WORK / "review.html"

UA_BASE = "lexi2-illustration-fetcher/1.0"
ALLOWED_HOSTS = ("commons.wikimedia.org", "upload.wikimedia.org")
LICENCE_RE = re.compile(r"^(Public domain|CC0|CC BY \d\.\d)$")
MAX_BYTES = 260 * 1024
MAX_EDGE = 700
RESIZE_EDGE = 640
MIN_W, MIN_H = 800, 500

# Title words that almost never make a good dictionary illustration.
TITLE_BLACKLIST = re.compile(
    r"logo|coat of arms|flag of|map of|chart|diagram|screenshot|poster|"
    r"signature|autograph|book cover|album cover|title page|banknote|stamp|"
    r"\bcart\b|carriage|wagon|\bmarket\b|\bfair\b|festival|\brace\b|\bgame of|"
    r"\bhunt|dish\b|cuisine|recipe|\bstew\b|\bsoup\b|\bteam\b|\bclub\b", re.I)

# Head-sense anchors per category. "start" patterns must match the beginning
# of the head sense; "words" patterns match anywhere (loose, lower priority).
CATEGORIES = {
    "animais": {
        "start": r"(Animal|Ave|Peixe|Insecto|Mamífero|Réptil|Anfíbio|Molusco|Crustáceo|"
                 r"Quadrúpede|Verme|Serpente|Víbora|Águia|Falcão|Gavião|Coruja|Pombo|Pato|"
                 r"Ganso|Perdiz|Codorniz|Inseto|Reptil|Anfibio|Crustaceo)",
        "words": r"\banimal|\bave\b|\bave,|\bpeixe|insecto|mamífero|réptil|anfíbio|molusco|"
                 r"crustáceo|quadrúpede|verme|serpente|pássaro|passaro|mariposa|borboleta|"
                 r"abelha|formiga|mosca|pulga|gato|cão\b|cão,|cavalo|carneiro|cabra|coelho|"
                 r"lobo|raposa|urso|leão|camelo|macaco|roedor|ruminante|aracnídeo|cefalópode",
        "relation": r"^(Fêmea do|Femea do|Macho da|Macho do|Machos de|Filhote|Cria d)",
    },
    "plantas": {
        "start": r"(Planta|Árvore|Arbusto|Erva|Fruto|Flor|Gramínea|Leguminosa|Umbelífera|"
                 r"Ciperácea|Musgo|Alga)",
        "words": r"\bplanta|árvore|arvore|arbusto|\berva\b|fruto d|flor\b|gramínea|leguminosa|musgo|alga",
    },
    "alimentos": {
        "start": r"(Substância alimentícia|Alimento|Manjar|Bebida|Sobremesa|Caldo)",
        "words": r"alimentícia|alimentício|alimento|manjar|comida|sobremesa|bebida",
    },
    "objectos": {
        "start": r"(Instrumento|Utensílio|Máquina|Ferramenta|Aparelho|Vaso|Objecto|Arma|Móvel|"
                 r"Tecido|Peça de)",
        "words": r"instrumento|utensílio|máquina|ferramenta|aparelho|vaso\b|objecto|peça de|arma\b|móvel\b|tecido",
    },
    "vestuario": {
        "start": r"(Vestuário|Calçado|Peça de vestuário)",
        "words": r"vestuário|calçado|roupa\b|cobertura de",
    },
    "corpo": {
        "start": r"(Órgão|Orgão|Osso|Cavidade|Glândula|Membrana|Nervo|Músculo|Parte do corpo)",
        "words": r"parte do corpo|órgão|orgão|\bosso\b|ossos|cavidade|glândula|membrana|nervo|músculo",
    },
    "lugares": {
        "start": r"(Edifício|Casa|Torre|Igreja|Palácio|Fortaleza|Castelo|Praça|Estrada|Túnel|Lugar)",
        "words": r"lugar\b|sítio\b|edifício|casa\b|torre\b|igreja|palácio|fortaleza|castelo|praça|rua\b|estrada|túnel",
    },
    "natureza": {
        "start": r"(Elevação|Monte|Serra|Rio|Lago|Mar|Ilha|Praia|Baía|Cabo|Gruta|Caverna|Fonte|"
                 r"Cascata|Deserto|Floresta|Mata|Pântano)",
        "words": r"elevação|monte\b|serra\b|\brio\b|\blago\b|\bmar\b|\bilha\b|praia\b|baía|cabo\b|gruta|"
                 r"caverna|fonte\b|cascata|deserto|floresta|mata\b|pântano",
    },
    "transportes": {
        "start": r"(Embarcação|Veículo|Navio|Barco|Carruagem|Aeróstato)",
        "words": r"veículo|embarcação|navio|barco|carruagem|aeróstato|aviação",
    },
    "musica": {
        "start": r"(Instrumento músico|Instrumento musical)",
        "words": r"instrumento músico|instrumento musical",
    },
}


def http_json(url, contact):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(contact)})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def http_bytes(url, contact):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(contact)})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def user_agent(contact):
    if contact:
        return "%s (%s)" % (UA_BASE, contact)
    return "%s (no contact configured; set --contact or LEXI_CONTACT)" % UA_BASE


def load_headwords():
    """lemma -> (pos, first sense text)."""
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    heads = {}
    for key in meta["keys"]:
        path = DATA / ("%s.json" % key)
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8")):
            pos = row[1]
            if isinstance(pos, list):
                pos = " ".join(str(x) for x in pos)
            senses = row[2]
            first = ""
            if isinstance(senses, list) and senses and isinstance(senses[0], list):
                first = senses[0][0]
            heads[row[0]] = (pos, first)
    return heads


def manifest_lemmas():
    if not MANIFEST.exists():
        return set()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {r["lemma"] for r in manifest.get("images", [])}


def classify(first):
    """Return (category, match) for a head sense, or (None, None)."""
    low = first.lower()
    for cat, spec in CATEGORIES.items():
        if re.match(spec["start"], first):
            return cat, "strict"
    for cat, spec in CATEGORIES.items():
        if spec.get("relation") and re.match(spec["relation"], first):
            return cat, "relation"
    for cat, spec in CATEGORIES.items():
        if re.search(spec["words"], low):
            return cat, "broad"
    return None, None


def cmd_queue(args):
    heads = load_headwords()
    done = manifest_lemmas()
    entries = []
    for lemma in sorted(heads):
        if lemma in done:
            continue
        pos, first = heads[lemma]
        if not re.search(r"\bm\.|\bf\.", pos) or not first:
            continue
        cat, match = classify(first)
        if not cat:
            continue
        if args.category and cat != args.category:
            continue
        entries.append({
            "lemma": lemma,
            "category": cat,
            "match": match,
            "sense": first[:110],
            "query": lemma,
            "status": "pending",
            "file": None,
        })
    # Strict matches first, then relation, then broad; alphabetical inside.
    order = {"strict": 0, "relation": 1, "broad": 2}
    entries.sort(key=lambda e: (order[e["match"]], e["lemma"]))

    existing = []
    if QUEUE.exists() and not args.rebuild:
        try:
            existing = json.loads(QUEUE.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    kept = {e["lemma"]: e for e in existing if e.get("status") != "pending"}
    merged = []
    for e in entries:
        old = kept.pop(e["lemma"], None)
        merged.append(old if old else e)
    merged.extend(kept.values())  # entries no longer proposed (already done)

    WORK.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = {}
    for e in merged:
        counts[(e["match"], e["status"])] = counts.get((e["match"], e["status"]), 0) + 1
    print("queue: %d entries -> %s" % (len(merged), QUEUE))
    for (match, status), n in sorted(counts.items()):
        print("  %-8s %-12s %d" % (match, status, n))


def pick_query(entry, args):
    return (args.query_override or entry.get("query") or entry["lemma"]).strip()


def search_candidates(query, contact):
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
    data = http_json(url, contact)
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
            "credit": val("Credit")[:120],
            "width": ii.get("width", 0),
            "height": ii.get("height", 0),
            "mime": ii.get("mime", ""),
            "url": ii.get("url", ""),
            "thumburl": ii.get("thumburl") or ii.get("url", ""),
            "descriptionurl": ii.get("descriptionurl", ""),
        })
    return out


def score_candidate(cand, lemma):
    if not LICENCE_RE.match(cand["licence"]):
        return None
    if cand["mime"] not in ("image/jpeg", "image/png"):
        return None
    w, h = cand["width"], cand["height"]
    if w < MIN_W or h < MIN_H:
        return None
    ratio = w / float(h)
    if ratio < 0.35 or ratio > 2.8:
        return None
    title = cand["title"]
    if TITLE_BLACKLIST.search(title):
        return None
    fold = lambda s: "".join(ch for ch in unicodedata.normalize("NFKD", s.lower())
                             if not unicodedata.combining(ch))
    score = 0.0
    tl = fold(title)
    lf = fold(lemma)
    words = lf.split()
    first_word = words[0] if words else lf
    # Subject-like titles win; scene/event titles lose.
    n_title_words = len(tl.replace("file:", "").split())
    if n_title_words <= 3:
        score += 2
    elif n_title_words >= 6:
        score -= 2
    if re.search(r"\b%s\b" % re.escape(lf), tl):
        score += 3
    if re.search(r"\b%s\b" % re.escape(first_word), tl):
        score += 1
    if re.search(r"\b(painting|pintura|engraving|gravura|drawing|desenho|statue|estátua|estatua)\b", tl):
        score -= 1
    if w >= 1200:
        score += 0.5
    if w >= h:
        score += 0.25
    return score


def resize_to_jpeg(src, dest):
    """Downscale to RESIZE_EDGE and re-encode as JPEG quality 78 (sips, then PIL)."""
    try:
        r = subprocess.run(
            ["sips", "-Z", str(RESIZE_EDGE), "-s", "format", "jpeg",
             "-s", "formatOptions", "78", str(src), "--out", str(dest)],
            capture_output=True, text=True)
        if r.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    try:
        from PIL import Image  # type: ignore
        img = Image.open(src).convert("RGB")
        img.thumbnail((RESIZE_EDGE, RESIZE_EDGE))
        img.save(dest, "JPEG", quality=78)
        return True
    except Exception:
        return False


def jpeg_size(path):
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


def file_stem(lemma):
    fold = "".join(ch for ch in unicodedata.normalize("NFKD", lemma)
                   if not unicodedata.combining(ch))
    stem = re.sub(r"[^A-Za-z0-9-]+", "-", fold).strip("-").lower()
    return stem or "lemma"


def choose_candidate(args, lemma):
    """Re-fetch lemma using candidate #N from its existing record (--choose N)."""
    stem = file_stem(lemma)
    rec_path = WORK / "records" / (stem + ".json")
    if not rec_path.exists():
        print("no record for %s" % lemma)
        return False
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    cands = rec.get("candidates") or []
    if not (1 <= args.choose <= len(cands)):
        print("%s: --choose %d out of range (1-%d)" % (lemma, args.choose, len(cands)))
        for i, c in enumerate(cands, 1):
            print("  %2d. %s | %s" % (i, c["title"][:70], c["licence"]))
        return False
    cand = cands[args.choose - 1]
    filename = rec["file"]
    src = WORK / "images" / filename
    for attempt in range(3):
        try:
            contact = args.contact or None
            blob = http_bytes(cand["thumburl"], contact)
            src.write_bytes(blob)
            break
        except Exception as e:
            wait = 60 * (attempt + 1)
            print("  download failed (%s); waiting %ds" % (e, wait))
            time.sleep(wait)
    else:
        return False
    if not resize_to_jpeg(src, src):
        print("  could not resize")
        return False
    size = jpeg_size(src)
    data = src.read_bytes()
    rec.update({
        "author": cand.get("artist") or "Unknown",
        "licence": cand["licence"],
        "licence_url": licence_url(cand["licence"]),
        "source": cand["source"],
        "retrieved": time.strftime("%Y-%m-%d"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "width": size[0] if size else 0,
        "height": size[1] if size else 0,
        "chosen_title": cand["title"],
    })
    rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("chose #%d for %s: %s | %s (%d bytes)" % (
        args.choose, lemma, cand["title"][:60], cand["licence"], len(data)))
    return True


def cmd_fetch(args):
    contact = args.contact or None
    if not contact:
        print("warning: no --contact given; Wikimedia asks for a reachable contact in the User-Agent.")
    queue = json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else []
    if not queue:
        print("no queue; run the queue command first")
        return 1
    done_files = {e.get("file") for e in queue if e.get("file")}
    if args.lemmas and not args.choose:
        wanted = [w.strip() for w in args.lemmas.split(",") if w.strip()]
        todo = [e for e in queue if e["lemma"] in wanted]
        missing = set(wanted) - {e["lemma"] for e in todo}
        if missing:
            print("not in queue: %s" % ", ".join(sorted(missing)))
        # Explicit refetch: retire previous candidates for these lemmas.
        for e in todo:
            old = e.get("file")
            if old:
                done_files.discard(old)
                for p in [WORK / "images" / old, WORK / "records" / old.replace(".jpg", ".json")]:
                    if p.exists():
                        p.unlink()
                e["file"] = None
    else:
        todo = [e for e in queue if e.get("status") == "pending"][:args.limit]

    (WORK / "images").mkdir(parents=True, exist_ok=True)
    (WORK / "records").mkdir(parents=True, exist_ok=True)

    fetched = 0
    if args.choose:
        if not args.lemmas:
            print("--choose needs --lemmas")
            return 1
        ok = all(choose_candidate(args, w.strip()) for w in args.lemmas.split(",") if w.strip())
        return 0 if ok else 1
    for entry in todo:
        lemma = entry["lemma"]
        if entry.get("status") == "fetched" and not args.lemmas:
            continue
        query_text = pick_query(entry, args)
        queries = [q.strip() for q in query_text.split("|") if q.strip()] or [lemma]
        print("[%s] searching: %s" % (lemma, " | ".join(queries)))
        cands, seen_titles = [], set()
        try:
            for qi, query in enumerate(queries):
                if qi:
                    time.sleep(args.delay)
                for c in search_candidates(query, contact):
                    if c["title"] not in seen_titles:
                        seen_titles.add(c["title"])
                        cands.append(c)
        except Exception as e:
            print("  search failed: %s" % e)
            entry["status"] = "error"
            entry["error"] = str(e)[:200]
            time.sleep(args.delay)
            continue
        scored = []
        for c in cands:
            s = score_candidate(c, lemma)
            if s is not None:
                scored.append((s, c))
        scored.sort(key=lambda sc: -sc[0])
        if not scored:
            print("  no acceptable candidate (%d raw hits)" % len(cands))
            entry["status"] = "no-candidate"
            time.sleep(args.delay)
            continue

        score, best = scored[0]
        stem = file_stem(lemma)
        filename = stem + ".jpg"
        n = 2
        while filename in done_files:
            filename = "%s-%d.jpg" % (stem, n)
            n += 1
        src = WORK / "images" / filename
        ok = False
        for attempt in range(3):
            try:
                blob = http_bytes(best["thumburl"], contact)
                src.write_bytes(blob)
                ok = True
                break
            except Exception as e:
                wait = 60 * (attempt + 1)
                print("  download failed (%s); waiting %ds" % (e, wait))
                time.sleep(wait)
        if not ok:
            entry["status"] = "error"
            entry["error"] = "download failed"
            continue
        if not resize_to_jpeg(src, src):
            print("  could not resize (sips/PIL unavailable)")
            entry["status"] = "error"
            entry["error"] = "resize failed"
            continue
        size = jpeg_size(src)
        data = src.read_bytes()
        record = {
            "file": filename,
            "lemma": lemma,
            "caption": {"pt-PT": lemma, "en": lemma},
            "alt": {"pt-PT": lemma, "en": lemma},
            "author": best["artist"] or "Unknown",
            "licence": best["licence"],
            "licence_url": licence_url(best["licence"]),
            "source": best["descriptionurl"],
            "retrieved": time.strftime("%Y-%m-%d"),
            "modified": "Resized to %d px and re-encoded as JPEG (quality 78)." % RESIZE_EDGE,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "width": size[0] if size else 0,
            "height": size[1] if size else 0,
            "query": query_text,
            "chosen_title": best["title"],
            "alternates": [
                {"title": c["title"], "url": c["descriptionurl"], "licence": c["licence"]}
                for s, c in scored[1:6]
            ],
            "candidates": [
                {"title": c["title"], "licence": c["licence"], "thumburl": c["thumburl"],
                 "source": c["descriptionurl"], "artist": c["artist"],
                 "width": c["width"], "height": c["height"]}
                for s, c in scored[:12]
            ],
        }
        (WORK / "records" / (stem + ".json")).write_text(
            json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        entry["status"] = "fetched"
        entry["file"] = filename
        done_files.add(filename)
        fetched += 1
        print("  -> %s | %s | %s (%d bytes)" % (
            filename, best["licence"], best["title"][:60], len(data)))
        time.sleep(args.delay + random.uniform(0, args.delay * 0.4))

    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("fetched %d, queue saved" % fetched)
    return 0


def licence_url(licence):
    m = re.match(r"^CC BY (\d\.\d)$", licence)
    if m:
        return "https://creativecommons.org/licenses/by/%s/" % m.group(1)
    if licence == "CC0":
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    return ""


def cmd_report(args):
    queue = json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else []
    fetched = [e for e in queue if e.get("status") == "fetched" and e.get("file")]
    rows = []
    for e in fetched:
        stem = file_stem(e["lemma"])
        rec_path = WORK / "records" / (stem + ".json")
        if not rec_path.exists():
            continue
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        rec["_category"] = e.get("category")
        rec["_match"] = e.get("match")
        rec["_sense"] = e.get("sense")
        rows.append(rec)
    rows.sort(key=lambda r: (r.get("_category") or "", r["lemma"]))

    parts = ["""<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<title>Lexi2 — review de ilustrações</title>
<style>
body{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:16px;color:#153d52;max-width:1100px}
h1{font-size:20px} p{font-size:13px;color:#555}
table{border-collapse:collapse;width:100%}
td,th{border:1px solid #ccd;padding:6px;vertical-align:top;font-size:13px;text-align:left}
img{max-width:220px;max-height:150px;display:block}
.sel{width:24px}
textarea{width:100%;height:120px;margin-top:10px;font-family:monospace;font-size:12px}
button{margin:8px 0;padding:6px 12px}
.sense{color:#666;font-style:italic}
</style>
</head>
<body>
<h1>Review de ilustrações — selecção humana</h1>
<p>Confirme as imagens aceitáveis, ajuste as legendas e copie o JSON abaixo para um
ficheiro (por exemplo <code>.work/illustrations-auto/selection.json</code>). Só o que
estiver na selecção é integrado. Licenças aceites: domínio público, CC0, CC BY.</p>
<table><tr><th>✓</th><th>Imagem</th><th>Lema</th><th>Sentido (dicionário)</th><th>Legenda pt-PT</th><th>Legenda en</th><th>Créditos</th></tr>"""]
    for r in rows:
        lic = r["licence"]
        if r.get("licence_url"):
            lic = '<a href="%s">%s</a>' % (r["licence_url"], lic)
        parts.append(
            '<tr data-lemma="%s">'
            '<td class="sel"><input type="checkbox" class="pick"></td>'
            '<td><img src="images/%s" loading="lazy"><br><small>%dx%d · %d bytes</small></td>'
            '<td><strong>%s</strong><br><small>%s / %s</small></td>'
            '<td class="sense">%s</td>'
            '<td><input class="cap-pt" value="%s"></td>'
            '<td><input class="cap-en" value="%s"></td>'
            '<td>%s · %s · <a href="%s">origem</a>'
            '<br><small>alternativas: %s</small></td>'
            '</tr>' % (
                html_attr(r["lemma"]), r["file"], r["width"], r["height"], r["bytes"],
                html_attr(r["lemma"]), r.get("_category") or "", r.get("_match") or "",
                html_attr(r.get("_sense") or ""),
                html_attr(r["caption"]["pt-PT"]), html_attr(r["caption"]["en"]),
                html_attr(r["author"]), lic, html_attr(r["source"]),
                html_attr("; ".join(a["title"] for a in r.get("alternates", [])[:3])),
            ))
    parts.append("""</table>
<button onclick="build()">Actualiza selecção</button>
<p>Selecção (JSON — copie para <code>selection.json</code>):</p>
<textarea id="out"></textarea>
<script>
function build(){
 var rows=[].slice.call(document.querySelectorAll('tr[data-lemma]'));
 var out=[];
 rows.forEach(function(tr){
  if(!tr.querySelector('.pick').checked)return;
  out.push({lemma:tr.getAttribute('data-lemma'),
   caption:{'pt-PT':tr.querySelector('.cap-pt').value,
            'en':tr.querySelector('.cap-en').value}});
 });
 document.getElementById('out').value=JSON.stringify(out,null,1);
}
document.querySelectorAll('.pick').forEach(function(cb){cb.addEventListener('change',build)});
build();
</script>
</body></html>""")
    REVIEW.write_text("\n".join(parts), encoding="utf-8")
    print("review page: %s (%d candidates)" % (REVIEW, len(rows)))
    return 0


def html_attr(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def cmd_status(args):
    queue = json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else []
    counts = {}
    for e in queue:
        counts[e.get("status", "?")] = counts.get(e.get("status", "?"), 0) + 1
    print("queue: %d entries | %s" % (len(queue), ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    next_pending = [e["lemma"] for e in queue if e.get("status") == "pending"][:10]
    if next_pending:
        print("next pending: %s" % ", ".join(next_pending))


def cmd_integrate(args):
    if args.selection_file:
        selection = json.loads(Path(args.selection_file).read_text(encoding="utf-8"))
    elif args.selection:
        selection = [{"lemma": w.strip()} for w in args.selection.split(",") if w.strip()]
    else:
        print("nothing selected; use --selection-file or --selection")
        return 1
    if args.dry_run:
        print("dry run — nothing will be written")

    heads = load_headwords()
    done = manifest_lemmas()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    total = sum(r["bytes"] for r in manifest["images"])
    added, skipped = 0, []

    for item in selection:
        lemma = (item.get("lemma") or "").strip()
        if not lemma:
            continue
        if lemma in done:
            skipped.append((lemma, "already illustrated"))
            continue
        if lemma not in heads:
            skipped.append((lemma, "not a headword"))
            continue
        stem = file_stem(lemma)
        rec_path = WORK / "records" / (stem + ".json")
        img_path = WORK / "images" / (stem + ".jpg")
        if not rec_path.exists() or not img_path.exists():
            skipped.append((lemma, "no fetched candidate"))
            continue
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        if not LICENCE_RE.match(rec["licence"]):
            skipped.append((lemma, "licence not accepted: %s" % rec["licence"]))
            continue
        host = urllib.parse.urlparse(rec["source"]).netloc.lower()
        if host and host not in ALLOWED_HOSTS:
            skipped.append((lemma, "source host not allowed: %s" % host))
            continue
        data = img_path.read_bytes()
        if len(data) > MAX_BYTES:
            skipped.append((lemma, "file too large"))
            continue
        size = jpeg_size(img_path)
        if not size or max(size) > MAX_EDGE:
            skipped.append((lemma, "bad dimensions"))
            continue
        if hashlib.sha256(data).hexdigest() != rec["sha256"]:
            skipped.append((lemma, "sha mismatch"))
            continue
        caption = item.get("caption") or rec["caption"]
        entry = {
            "file": rec["file"], "lemma": lemma,
            "caption": {"pt-PT": caption.get("pt-PT") or lemma,
                        "en": caption.get("en") or lemma},
            "alt": {"pt-PT": caption.get("pt-PT") or lemma,
                    "en": caption.get("en") or lemma},
            "author": rec["author"], "licence": rec["licence"],
            "licence_url": rec.get("licence_url", ""), "source": rec["source"],
            "retrieved": rec["retrieved"], "modified": rec["modified"],
            "sha256": rec["sha256"], "bytes": rec["bytes"],
            "width": rec["width"], "height": rec["height"],
        }
        print("integrate %-14s %7d bytes %dx%d | %s" % (
            entry["file"], entry["bytes"], entry["width"], entry["height"], entry["licence"]))
        if not args.dry_run:
            (IMAGES / rec["file"]).write_bytes(data)
            manifest["images"].append(entry)
            total += entry["bytes"]
            manifest["bytes"] = total
            manifest["generated"] = time.strftime("%Y-%m-%d")
        added += 1

    if not args.dry_run and added:
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "check_images.py"), "--write"],
                       check=True)
    if skipped:
        print("skipped:")
        for lemma, why in skipped:
            print("  %-14s %s" % (lemma, why))
    print("integrated %d of %d selected%s" % (
        added, len(selection), " (dry run)" if args.dry_run else ""))
    if added and not args.dry_run:
        print("reminder: cached runtime files changed — bump LEXI_VERSION in version.js")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("queue", help="build/rebuild the candidate queue")
    q.add_argument("--category", choices=sorted(CATEGORIES), help="only this category")
    q.add_argument("--rebuild", action="store_true", help="discard previous queue state")
    q.set_defaults(func=cmd_queue)

    f = sub.add_parser("fetch", help="fetch candidates for pending entries")
    f.add_argument("--limit", type=int, default=25, help="max lemmas this run")
    f.add_argument("--lemmas", help="comma-separated lemmas (overrides queue order)")
    f.add_argument("--query-override", help="override search text for --lemmas run")
    f.add_argument("--choose", type=int, help="with --lemmas: pick candidate #N from the saved record")
    f.add_argument("--delay", type=float, default=5.0, help="base delay between requests (s)")
    f.add_argument("--contact", default=None, help="contact for the User-Agent (or LEXI_CONTACT)")
    f.set_defaults(func=cmd_fetch)

    r = sub.add_parser("report", help="write the human review page")
    r.set_defaults(func=cmd_report)

    s = sub.add_parser("status", help="queue progress summary")
    s.set_defaults(func=cmd_status)

    i = sub.add_parser("integrate", help="copy selected lemmas into the app")
    i.add_argument("--selection-file", help="JSON from the review page")
    i.add_argument("--selection", help="comma-separated lemmas (captions from fetch records)")
    i.add_argument("--dry-run", action="store_true")
    i.set_defaults(func=cmd_integrate)

    args = ap.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
