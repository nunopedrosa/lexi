# Lexi2

A local-first European Portuguese dictionary PWA. Lexi2 is a new corpus built by
crossing the **words-pt** form inventory with **Dicionário Aberto**, with a
lemma-first data model, an explicit missing-lemma report and review flags for
historical definitions.

The project has a working corpus pipeline, a static sharded PWA shell and a
reviewed illustration set. It is still a data-and-review phase project: the
dictionary is not human-reviewed lexicography, and device verification and
deployment remain separate, explicit steps.

## Source strategy

- **words-pt** supplies the Portuguese form inventory and its GPL-3.0 licensing.
- **Dicionário Aberto** supplies the historical definitions (1913, CC BY-SA 2.5
  PT) and their regional/usage labels.
- **Hunspell pt_PT** supplies the modern lemma layer, explicit form-to-lemma
  links and `PREAO90` spelling metadata, so the comparison is lemma-based rather
  than a naive form-to-form match.

The pipeline does not silently rewrite Dicionário Aberto. It preserves the
original text, produces a separately flagged automatic modernisation suggestion,
and records review flags. The missing-word deliverable is a **lemma-only list**,
not a raw dump of every inflected form. Missing lemmas that exist in the pinned
sibling Lexi snapshot (Wiktionary via kaikki.org) additionally carry a labelled,
unreviewed Wiktionary bridge definition; see "Wiktionary bridge layer" below.

## Build the corpus

Requirements: Python 3.9 or newer. No runtime dependencies.

```sh
python3 scripts/fetch_sources.py
python3 scripts/build_corpus.py
python3 scripts/build_pwa_data.py
```

The full corpus build uses the build-time `hunspell` command for the
form-to-lemma index. Use `python3 scripts/build_corpus.py --no-forms` only for a
reduced diagnostic build; the PWA needs `build/forms.json`.

`fetch_sources.py` downloads the pinned snapshots into `.work/sources/`, verifies
their SHA-256 hashes and extracts them. `build_corpus.py` writes:

- `build/da-entries.jsonl` — Dicionário Aberto entries and senses with flags;
- `build/lemmas.jsonl` — the modern lemma universe and its match status;
- `build/forms.json` and `build/forms-meta.json` — the Hunspell-generated
  form-to-lemma index (requires the `hunspell` command; use `--no-forms` to skip);
- `build/words-pt-coverage.json` — how much of words-pt the form/lemma indexes
  cover;
- `build/audit.json` — counts, distributions and pipeline checks;
- `docs/missing-lemmas.csv` and `docs/missing-lemmas.json` — the lemma-only
  missing list (the primary deliverable);
- `docs/CORPUS.md` — the generated human-readable report;
- `data/` — the sharded PWA dictionary, form index and missing index (about
  44 MB uncompressed).

`build/` is an intermediate directory and is not committed. The missing list,
the report, the source documentation and the generated `data/` shards are the
reviewable outputs.

## Run the PWA locally

```sh
python3 -m http.server 8009
```

Open `http://localhost:8009/`. The service worker works on localhost or HTTPS.
The app currently presents the Dicionário Aberto source text with usage labels,
PT-PT-first ordering, a separately flagged automatic spelling suggestion and
the missing-lemma response. Entries whose senses are all labelled Brazilian are
marked, and DA headwords outside the modern PT-PT lexicon used for matching are
marked historical. A small, sense-dependent PT-PT/PT-BR correspondence table
provides an equivalent when the source or the missing list has no PT-PT form.
A browsable missing-list page at `missing.html` supports search and
priority/POS/source filters. It does not yet have syllable search.

### Personal definitions

Each entry offers **Add my definition** (or **Edit my definition** when one
exists). The text is stored in `localStorage` under `lexi2.userDefinitions`,
keyed by the resolved lemma, so a definition added through an inflected form or
an old spelling appears under the lemma itself. It is shown as a separate,
labelled bubble directly below the dictionary definition, or below the
missing-lemma notice when the word has no entry at all. It is never merged into
the source text and never presented as reviewed.

The personal layer is local to the device and browser. It is included in the
backup export (`schema: 2`, `personalDefinitions`); the import still accepts
`schema: 1` files, which contain no definitions. Importing merges definitions by
lemma and replaces a matching local entry. Each definition is limited to 600
characters and the store to 2,000 entries; there is no sync between devices.

### Illustrations

A reviewed set of 525 illustrations is bundled in `images/` and shown as a
captioned figure under the matching entry. The full lemma list with captions is
in `docs/IMAGES.md`. The set is deliberately not exhaustive:
only concrete words with a clear sense are illustrated, and an image never
replaces or supports a definition.

When a lemma has no bundled illustration, the entry shows a user-initiated
Google Images link whose query combines the lemma with the current sense and
prefers Wikimedia Commons or public-domain results. Opening the link stores a
local `wanted` tag with the query and search URL. Like the replacement tags, it
stays on the device and leaves it only in an exported backup; it is not merged
into the dictionary. `scripts/apply_image_tags.py` reports these requests and,
with `--refetch`, prints Commons candidates for review. Adding a new
illustration still needs a human-written caption and alt text in both languages.

Each file is a local copy (there is no hotlinking), resized to 640 px and
re-encoded as JPEG; the set is about 50.4 MB. Sources are Wikimedia Commons and
the Metropolitan Museum of Art Open Access collection; licences are public
domain, CC0 or CC BY, never NC, ND or SA. `images/manifest.json` records the
lemma, captions and alt text in both languages, author, licence, source page,
retrieval date, SHA-256 and dimensions. `credits.html` lists every image and is
linked from Settings.

Run `python3 scripts/check_images.py` to verify hashes, sizes, dimensions,
licences and that every illustrated lemma is a dictionary headword; `--write`
regenerates `docs/IMAGES.md` and `credits.html` from the manifest. The images are
included in the offline preparation.

To grow the set without an LLM, `scripts/fetch_illustrations.py` automates
candidate sourcing from Wikimedia Commons at a slow, resumable pace:
`queue` builds a lemma queue from the dictionary head senses,
`fetch` downloads and pre-verifies candidates (public domain, CC0 or CC BY
only, 640 px JPEG, bounded per run with `--limit`), `report` writes a local
review page at `.work/illustrations-auto/review.html` where a human approves
images and writes the captions, and `integrate --selection-file` copies only
the approved lemmas into `images/` and the manifest. Automation proposes; the
selection file is the human decision that gates what is committed.

Use `python3 scripts/fetch_sources.py --check` to verify existing snapshots
without downloading, and `--force` to refresh them.

## Current corpus status

- 128,520 Dicionário Aberto entries and 152,395 latest-revision senses.
- 127,930 runtime headwords after merging modern lemmas and the Wiktionary
  bridge layer.
- 28,591 modern lemmas matched; 6,139 lemma-only missing entries, of which
  2,564 carry a labelled, unreviewed Wiktionary bridge definition (2,549 on
  the modern spelling, 15 through the pre-AO spelling); 41 approved editorial
  definitions.
- 908,678 form-index rows. 816,163 words-pt forms resolve to a matched lemma;
  122,793 resolve only to a missing lemma; 59,474 remain unresolved.
- M1 review queue: 274 lemmas after 149 reviewed pre-AO pairs and 41 approved
  editorial definitions; 99 of them carry the Wiktionary bridge layer. M2:
  5,865.
- Coverage: 89.0% of Portuguese tokens in a two-PDF sample; 79.8% on the
  12,036-word coverage list (many unknowns are OCR fragments and proper names).
- About 92 MiB of uncompressed runtime data, including the dictionary shards
  (about 44 MiB) and the 50 MB illustration set.
- Not done yet: human review, semantic-drift verification, full offline/cache
  testing, Safari 12 / iPhone 6 device verification and a verified deployment.

### Wiktionary bridge layer

Missing lemmas that also exist in the sibling Lexi snapshot (Portuguese and
English Wiktionary via kaikki.org, CC BY-SA 4.0) are shipped with a labelled,
unreviewed definition layer. The senses are flagged `wikt`, shown with an
explicit unreviewed notice, and never merged into the Dicionário Aberto text.
The snapshot's Brazilian labels are preserved, a conservative
parenthetical-label scan marks further Brazilian senses, and entries whose
senses are all Brazilian are marked `br`. Where the snapshot had applied its
own unrevised automatic PT-PT adaptation, the original wording is restored and
the adapted text is kept as a separately flagged suggestion. The layer is not
human-reviewed; the source snapshot is pinned per file in `docs/SOURCES.md`.

## PDF coverage check

To measure how much of a Portuguese PDF the current dictionary covers:

```sh
python3 -m pip install --target .work/python pypdf
python3 scripts/pdf_coverage.py /path/to/pdfs --max-pages 200
```

The tool reads PDFs in place, extracts text, classifies tokens against the
dictionary, form index and missing list, and writes `docs/PDF-COVERAGE.md` and
`build/pdf-coverage.json`. It does not copy the PDFs or add them to the
dictionary. Scanned PDFs without an OCR text layer produce no useful text.

## Review queue

`docs/M1-MISSING.md` groups the 274 highest-priority missing lemmas, all of
them pre-AO-only after the 19 near-only candidates were reviewed and none was
safe to auto-link.
`docs/CURATED-DEFINITIONS.md` records the 22 curated lemmas whose approved PT-PT
definitions are integrated as a labelled editorial layer.
`docs/NEAR-ONLY-DEFINITIONS.md` records the 19 approved definitions for the
reviewed near-only lemmas.
`docs/M1-PROPOSED-BATCH.md` holds proposed, unintegrated definitions for the 35
highest-value pre-AO-only lemmas.

## Deployment

The host-side deployment profile is `scripts/deploy-profile.sh`; its default
destination is `~/lexi.basecentral.link` (override with `DEPLOY_SITE`), intended
to replace the existing Lexi site. The common engine is the vendored BaseCentral
deploy script. Deployment is a separate, explicit action. The deploy engine
preserves unrelated files, so old Lexi-only assets may need manual cleanup after
the replacement.

The profile publishes the app shell, the dictionary shards, `credits.html` and
every file in `images/`. Run `python3 scripts/check_publish.py` before
deploying: it fails if the service worker precaches an unpublished file or if
the illustration manifest and `images/` disagree. The deploy profile runs the
same check through `deploy_validate`, because a single missing precached file
aborts the service-worker install and with it update detection.

## Licences

The application code and generated dictionary database are released under
**GPL-3.0**. Dicionário Aberto material remains under **CC BY-SA 2.5 PT**;
words-pt and Hunspell pt_PT are under **GPL-3.0** and **GPL/LGPL/MPL**
respectively. See `LICENSE` and `ATTRIBUTION.md`.

## Status and limits

- The corpus is historical. Definitions may be obsolete, archaic, regional or
  wrong; they are not human-reviewed.
- Automatic spelling modernisation is a suggestion, not verified lexicography.
- The Wiktionary bridge layer is unreviewed third-party content (CC BY-SA 4.0,
  Wiktionary via kaikki.org). Its Brazilian labels are preserved where present;
  unmarked senses are not claimed to be European Portuguese.
- European Portuguese is the default presentation, but Brazilian and regional
  senses are preserved and labelled.
- Missing lemmas are those absent from the current Dicionário Aberto snapshot
  after conservative orthographic matching. They are not a claim that the word
  is absent from Portuguese.
- Personal definitions are the user's own wording. They are stored only on the
  device, are not part of the corpus or of any generated data, and are not
  reviewed or verified.
- Illustrations are illustrative only. The set covers 525 concrete lemmas, is
  not exhaustive and is not a substitute for a definition; each image keeps its
  own licence and attribution.
