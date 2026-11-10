# Lexi2 — agent instructions

Lexi2 is a local-first, static European Portuguese dictionary PWA. It has a
working corpus pipeline, sharded runtime data and a static shell adapted from
Lexi. The dictionary is not human-reviewed lexicography.

## Start here

- Read `README.md`, `docs/SOURCES.md` and the generated `docs/CORPUS.md` before
  changing the pipeline or the data contract.
- This project adopts the shared trekm / BaseCentral PWA baseline in
  [`../pwa/AGENTS.md`](../pwa/AGENTS.md), revision **2026-10-27, decision set 6**,
  including the **2026-11-01 shared controls and deployment addition**. Read the
  current shared file before each substantial change; this adoption record does
  not freeze it.
- If the sibling baseline is unavailable, report that it could not be checked.
  Do not silently substitute weaker rules.
- This adoption does not authorize corpus regeneration, storage migrations,
  releases, publication or deployment. Those require an explicit request.

## Corpus provenance and licences

- Lexi2 code and the generated dictionary database are **GPL-3.0**.
- Dicionário Aberto data is **CC BY-SA 2.5 PT** and must retain its attribution.
- words-pt is **GPL-3.0** and Hunspell pt_PT is **GPL/LGPL/MPL**. Preserve the
  notices in `ATTRIBUTION.md` and any source snapshot metadata.
- Do not remove source provenance or silently replace a source. Record the
  snapshot URL, date and SHA-256 in `docs/SOURCES.md` and `build/sources.json`.
- Source snapshots in `.work/` are downloaded material, not project-authored
  content. Do not commit them unless an explicit archival decision is made.

## Data pipeline rules

- The canonical entry model is **lemma-first**. Inflected forms resolve to a
  lemma; they do not each become a headword by default.
- Preserve every Dicionário Aberto sense and its original definition text. The
  modernised text is a separate, explicitly flagged suggestion. Never overwrite
  the original or present the suggestion as verified.
- Keep regional, Brazilian, archaic and obsolete labels from the source. Do not
  delete Brazilian or regional material to make an entry look more PT-PT.
  European Portuguese is the default presentation, not a licence to erase
  variants.
- The missing-word deliverable is the **lemma-only list** requested by the
  product owner. A full form-level diagnostic may be produced for internal
  checks, but it is not the public missing-word list.
- `sources/curated-lemmas.txt` is a reviewed lemma supplement and
  `sources/preao-supplement.txt` is a reviewed pre-AO spelling supplement. Do not
  auto-fill either file from unreviewed candidates.
  `sources/curated-definitions.txt` holds only approved editorial definitions;
  `docs/M1-PROPOSED-BATCH.md` holds proposals. Keep proposals explicitly
  unintegrated and unverified until approved.
- Orthographic matching is conservative. Record the match type (`exact`,
  `preao90`, `orthographic`, `accent`) or the miss reason. Do not claim that a
  spelling-normalised match is a semantic equivalence without review.
- Do not infer modern meanings, regional equivalents or Brazilian translations
  automatically. Those require reviewed editorial data.
- The Wiktionary bridge layer is a labelled, unreviewed third-party layer
  (sibling Lexi snapshot, CC BY-SA 4.0, Wiktionary via kaikki.org) that gives
  definition-less missing lemmas a definition. Senses are flagged `wikt`, are
  never merged into Dicionário Aberto senses, and are shown with an unreviewed
  notice. The snapshot is pinned per file in `scripts/fetch_sources.py` and
  recorded in `docs/SOURCES.md`; a changed sibling checkout fails verification.
  Expanding the layer beyond the missing-lemma list is a separate decision.
- Keep counts, reports, hashes and `docs/CORPUS.md` consistent with the generated
  files. If the source snapshot or matching rules change, regenerate and report
  the change.
- Keep the build deterministic and dependency-free at runtime. Python scripts are
  development/build tools only; the PWA must remain static.
- `scripts/build_pwa_data.py` is the bridge from the corpus to the runtime
  shards. Keep its row contract explicit:
  - dictionary row: `[headword, pos, senses, status]`, where `status` is `ok`,
    `br` (all senses labelled Brazilian) or `historical` (outside the modern
    PT-PT lexicon used for matching);
  - sense: `[text, region, flags, modernized, source]`, where `flags` is a list
    of codes such as `arch`, `reg`, `tech`, `old`, `mod`, `cit`, `rev`, `wikt`;
  - form row: `[form, display]` or `[form, [display, ...]]`;
  - missing row: `[lemma, pos, preao90, near_headword, near_entry_id, notes,
    priority, source, curated_note, wikt_headword]`, where `wikt_headword`
    names the Wiktionary bridge headword when the lemma is covered by that
    layer, and is empty otherwise.
  Do not silently change this contract without updating `app.js`, the service
  worker cache list and the report.
- The dictionary runtime data is about 44 MiB uncompressed; the 525 local
  illustrations add about 50 MB, so offline preparation is about 92 MiB.
  Offline preparation must download the
  dictionary, form and missing shards, report the size, allow cancellation and
  verify cache writes before claiming readiness.

## Illustrations

- Illustrations are local files in `images/`, linked to a lemma through
  `images/manifest.json`. Never hotlink: offline use and privacy both require
  local copies.
- Accept only public domain, CC0 or CC BY images. Do not add CC BY-SA, NC or ND
  material. Keep the author, licence and licence URL, source page, retrieval
  date and SHA-256 for every file.
- Generate `credits.html` and `docs/IMAGES.md` from the manifest with
  `python3 scripts/check_images.py --write`; do not hand-edit them.
- Illustrate only concrete words with a clear sense, and disambiguate the sense
  in the caption when a word has several. An image is not evidence for a
  definition and must never look like one.
- Images keep their own licences. They are not corpus data and do not change the
  GPL-3.0 licensing of the code or the dictionary database.
- Keep the set small and reviewed. Automation may propose candidates, but a
  human decides what is committed.
- Readers can tag an illustration for replacement (wrong / could be better /
  remove) in the app. Tags are local-only (`lexi2.imageTags`) and leave the
  device only inside an exported backup (`imageTags` section). Applying them is
  a build-time step (`scripts/apply_image_tags.py`): `remove` drops the entry;
  `wrong`/`better` replace the image from the tag's Commons URL, a stored fetch
  candidate (`--choose`) or a refetch, under the same licence rules above; then
  regenerate credits/docs and bump the release. Tags without a clear
  replacement stay pending and are never silently resolved.
- When no illustration is bundled, the app offers a user-initiated Google Images
  search described by the lemma and the current sense. Opening the link records
  a local `wanted` tag with the sense-specific query and the search URL. It is
  another `imageTags` entry, so it travels only in an exported backup.
  `scripts/apply_image_tags.py` reports `wanted` requests and can search Commons
  with `--refetch`, but does not add an illustration automatically: captions,
  alt text and licence review remain a human decision.

## Future PWA boundaries

- No backend, accounts, tracking, telemetry, analytics or uploads.
- Entry points are static files plus generated data shards. Keep the corpus on
  the device and keep the optional external dictionary link user-initiated.
- Required interface languages: English and European Portuguese (`pt-PT`),
  switchable immediately, with the shared top-right **Settings gear then native
  Language pull-down**.
- Required Settings: Language, Data and backups, Installation and offline help,
  Check for updates, Help and privacy, and the installed app version.
- The backup must cover the app's supported device preferences **and** the
  personal definitions the user writes locally. Personal definitions are
  optional user content stored in `localStorage` and shown as a separate,
  labelled layer; do not invent a broader records database, and never merge them
  into the dictionary or present them as reviewed.
- Personal definitions stay on the device. They may leave it only inside a
  backup file the user explicitly exports.
- The backup also carries the user's image replacement tags (`imageTags` in the
  `schema: 2` backup; import merges by lemma, newer timestamp winning). Like
  personal definitions, tags stay on the device and leave it only inside a
  backup file the user explicitly exports.
- Offline preparation must be bounded, cancellable and truthful. Distinguish the
  cached app shell from a prepared dictionary and state the download size.
- Render dictionary text as text or through explicit DOM construction. Never use
  `innerHTML` for corpus or imported content.
- Required compatibility target: **iPhone 6 / iOS 12.5.x / Safari 12**, in Safari
  and from the Home Screen, alongside modern browsers. Avoid unsupported syntax
  (`?.`, `??`, `||=`, `Array.prototype.at`, `String.prototype.replaceAll`,
  `Object.fromEntries`, `File.text()`). Do not claim device support without
  device evidence.
- Bump the single release identifier whenever cached runtime files change. Keep
  cache names, release metadata, documentation and the displayed version
  together.
- Deployment is a separate, explicit user action. Do not deploy, publish or add
  the app to the shared catalogue as part of a corpus task.

## Verification

- Run the pipeline checks: `python3 scripts/fetch_sources.py --check` and
  `python3 scripts/build_corpus.py --check`.
- Run `python3 scripts/check_images.py` to verify illustration hashes, sizes,
  dimensions, licences and lemma coverage.
- Run `python3 scripts/check_publish.py` to verify that the deploy allowlist
  covers every file the service worker precaches and every illustration, and
  that no unreferenced image would be published.
- The full build uses the build-time `hunspell` command to produce
  `build/forms.json`. Use `--no-forms` only for a reduced check; record that the
  form index was skipped.
- Verify source hashes, entry/sense counts, match counts, missing-lemma counts,
  form-index coverage and the generated report together.
- Inspect samples across common words, old spellings, Brazilian labels, regional
  labels and genuinely missing modern terms.
- Report what was actually verified. A successful build is not a linguistic
  review, and a modern browser test is not Safari 12 evidence.

## Audit snapshot (2026-11-09, updated 2026-11-10)

| Area | Status | Evidence |
| --- | --- | --- |
| Source discovery and licensing | Meets | Pinned URLs and SHA-256 for words-pt, Dicionário Aberto, Hunspell and the Natura lists; licences recorded in `ATTRIBUTION.md` and `docs/SOURCES.md`. |
| Corpus pipeline | Partial | 998,430 words-pt forms, 128,520 DA entries, 152,395 latest senses, 34,771 modern lemmas, 28,591 safe matches, 6,139 missing lemmas and 41 approved editorial definitions. The reviewed `sources/preao-supplement.txt` resolved 149 lemmas and the approved definitions cover 41 more; M1 is 274. Deterministic build and `--check`; no human review. |
| Missing-lemma deliverable | Partial | Lemma-only CSV/JSON with priority, pre-AO spelling, near-candidate hint and AO-list membership. Near candidates are explicitly not auto-linked. A 24-lemma curated supplement adds common PT-PT words absent from Hunspell; 2 match DA and 41 lemmas have approved editorial definitions (22 curated, 19 reviewed near-only). A browsable `missing.html` page supports search and priority/POS/source filters. `docs/M1-MISSING.md` is the focused review queue; `docs/CURATED-DEFINITIONS.md` and `docs/NEAR-ONLY-DEFINITIONS.md` record the approved definitions integrated as a labelled editorial layer, and `docs/M1-PROPOSED-BATCH.md` holds 35 proposed definitions for pre-AO-only lemmas that are not integrated. |
| Coverage check | Partial | `scripts/pdf_coverage.py` classifies extracted PDF or word-list tokens against the dictionary, form index and missing list. A two-PDF sample measured 89.0% known Portuguese tokens; the committed 12,036-word list measured 79.8%, with many unknowns being OCR fragments and proper names. |
| Form index | Partial | 908,977 form rows from `hunspell -s`, explicit `.dic` forms, DA aliases and pre-AO pairs; 816,163 words-pt forms have a matched lemma, 122,793 have only a missing lemma, 59,474 are unresolved. |
| PT-PT presentation | Partial | PT-PT/unmarked senses first, Brazilian senses labelled and last, entry statuses `ok`/`br`/`historical`, and a 57-term curated PT-PT/PT-BR table. Not a full PT-BR filter. |
| Review flags | Partial | Brazilian, regional, archaic, technical, popular, poetic, neologism, old spelling, citation and unreviewed flags; review priority P1/P2/P3. No semantic-drift verification. |
| PWA shell and languages | Partial | Headless Chromium checks at 320 px: search, form alias, missing response, regional note, modernized view, EN/pt-PT switch, Settings. No physical device or screen-reader test. |
| Personal definitions | Partial | Local-only definitions in `lexi2.userDefinitions`, keyed by lemma, shown as a labelled bubble below the source definition or the missing-lemma notice, with add/edit/remove and no merge into the dictionary. Included in the `schema: 2` backup (`personalDefinitions`); the import accepts `schema: 1` and merges by lemma. Headless Chromium checks: add, edit, remove, reload persistence, form-alias keying, live language switch, 320 px editor, export payload and import preview/merge. No device test and no sync. |
| Illustrations | Partial | 525 local JPEGs (about 50.4 MB) for concrete lemmas, sourced from Wikimedia Commons and the Met Open Access collection (public domain, CC0 and CC BY). `images/manifest.json` records author, licence, source, retrieval date, dimensions and SHA-256; `credits.html` and `docs/IMAGES.md` are generated. `scripts/fetch_illustrations.py` queues, fetches and pre-verifies candidates without an LLM; a human review page and selection file gate integration. Unillustrated entries and missing lemmas offer a sense-described, user-initiated Google Images search; opening it stores a local `wanted` tag that is exported with the image tags. Headless Chromium checks: figure and credit rendering at 320 px, sense-disambiguating captions, search callout for unlisted words and missing lemmas, EN/pt-PT captions, flagged search export, SW caching, and offline preparation requesting all files. No designer review and no device test. |
| Offline and updates | Partial | Offline preparation was exercised in headless Chromium through the DevTools protocol: all dictionary, form and missing shards were fetched and the app reported the dictionary ready offline. The service worker now precaches with `cache:'reload'`, and "Check for updates" waits for the installing worker and reports a failed/redundant install instead of "latest version"; headless Chromium verified detection after a release bump, activation and reload, and a failed check that kept the previous shell when a precached file was missing. Cache eviction and a true airplane-mode reload were not re-tested. |
| Safari 12 / iPhone 6 | Partial | Inherited compatibility work retained; no unsupported syntax intentionally added. Device verification is still missing. |
| Deployment | Partial | `scripts/deploy-profile.sh` publishes the app shell, the dictionary shards, `credits.html` and all 525 images; `scripts/check_publish.py`, also run by `deploy_validate`, fails on an unpublished precached file or manifest/image drift. The live copy at `lexi.basecentral.link` predates that guard and is missing `credits.html` and `images/`, so its service worker cannot install. Deployment remains an explicit user action; no deployment was made during this review. |
