# Sources and snapshots

The build is pinned to the snapshots below. `scripts/fetch_sources.py` verifies
the SHA-256 before extraction. A changed upstream file must be reviewed,
recorded here and reflected in `docs/CORPUS.md`; do not silently follow `master`
or `latest`.

| Source | Snapshot | Role | Licence |
| --- | --- | --- | --- |
| words-pt | `wordsList.zip`, word list dated 2020-03-02 | Portuguese form inventory | GPL-3.0 |
| Dicionário Aberto | `SQL/data-20151213.sql.xz`, dump dated 2015-12-13 | Historical definitions and usage labels | CC BY-SA 2.5 PT |
| Hunspell pt_PT | `hunspell-pt_PT-20251001.tar.gz` | Modern lemmas, explicit forms and `PREAO90` spelling metadata | GPL/LGPL/MPL |
| Natura wordlist AO | `wordlist-ao-latest.txt.xz`, 2025-10-01 | Modern-spelling form inventory used for orthographic matching | GPL/LGPL/MPL |
| Natura wordlist pre-AO | `wordlist-preao-latest.txt.xz`, 2025-10-01 | Pre-AO form inventory used to derive spelling pairs | GPL/LGPL/MPL |
| Wiktionary bridge | sibling Lexi `data/` snapshot, commit `900df5d9` (2026-11-08) | Labelled, unreviewed definition layer for missing lemmas | CC BY-SA 4.0 |

## URLs and hashes

| File | URL | SHA-256 |
| --- | --- | --- |
| `wordsList.zip` | <https://raw.githubusercontent.com/jfoclpf/words-pt/master/wordsList.zip> | `8459f51d8e0de19593be43b41a21c64a1026a84132e5410bd320c43fe93d8213` |
| `data-20151213.sql.xz` | <https://raw.githubusercontent.com/ambs/Dicionario-Aberto/master/SQL/data-20151213.sql.xz> | `a48a2f36d59815c44adf531b6453f7cc63998e2dfa48d25452d0be33affb6fa9` |
| `hunspell-pt_PT-latest.tar.gz` | <https://natura.di.uminho.pt/download/sources/Dictionaries/hunspell/LATEST/hunspell-pt_PT-latest.tar.gz> | `2066157087e83264484a6d564e1d85258fe2c5eddb9713a42d6f6cf06b0a2ed9` |
| `wordlist-ao-latest.txt.xz` | <https://natura.di.uminho.pt/download/sources/Dictionaries/wordlists/LATEST/wordlist-ao-latest.txt.xz> | `ac5fb0cd0359d6b4678dc3d93e3311e008367a23f187f893f8b37662dfec0344` |
| `wordlist-preao-latest.txt.xz` | <https://natura.di.uminho.pt/download/sources/Dictionaries/wordlists/LATEST/wordlist-preao-latest.txt.xz> | `aadc31a7c33315be84316f8235ed808f39d01c5a5a05c29e91e2da5a698c9f72` |

The Wiktionary bridge snapshot is local: `scripts/fetch_sources.py` copies the
27 entry files from the sibling `../lexi/data` directory into
`.work/sources/lexi-wikt/` and verifies each file against a pinned SHA-256.
The manifest hash of the 27 pinned files is
`d6072a1eccdf…` (see `build/sources.json` for the per-file list). The upstream
provenance is the Portuguese and English Wiktionary via kaikki.org
(wiktextract), compiled by the Lexi project at commit
`900df5d9906e5f6c411bf5a4afb9154e6420ca08` (2026-11-08). A changed sibling
checkout fails verification until the pins are reviewed and updated.

## What each source contributes

### words-pt

`wordsList` contains 998,430 unique forms, encoded as ISO-8859-1. 585,446 contain
hyphens, mostly enclitic verb forms; 412,984 do not. The list includes lemmas,
inflections, proper nouns, siglas, abbreviations and foreign terms. It is not a
lemma list and does not carry definitions.

The list is used as the form inventory and as the external check on coverage. The
lemma universe is derived from Hunspell pt_PT because words-pt does not expose
lemma identity.

### Dicionário Aberto

The 2015 dump contains 128,520 `word` rows for 125,277 unique headwords. The
latest revision of each entry contains 152,395 senses; the dump also contains
248,209 non-deleted revision rows across all revisions. The live API reported
`count = 128521` during the initial inspection; the pinned 2015 dump is the
build source. The one-entry difference is not reconciled and should not be
described as identical to the live service.

The dictionary is based on Cândido de Figueiredo's 1913 *Novo Dicionário da
Língua Portuguesa*. It contains obsolete spelling, archaic senses, regional
labels and Brazilian labels. It does not contain many twentieth- and
twenty-first-century terms (`comboio`, `autocarro`, `telemóvel`, `frigorífico`,
for example).

The XML entries provide `<form><orth>`, `<sense>`, `<gramGrp>`, `<usg>`,
`<def>`, `<etym>` and related elements. The build preserves the original
definition text and extracts the labels into explicit flags.

### Hunspell pt_PT

The `.dic` has 44,476 lines. After excluding punctuation, 38,045 entries are base
lemmas and 6,431 are explicit inflected forms with `[$lemma$...]` links. The
`PREAO90=` attribute occurs on 907 entries and gives the pre-AO spelling. The
`.aff` file supplies the inflection rules; the build uses the explicit forms and
the lemma metadata, not the full generated 1M-form expansion.

The dictionary includes proper nouns (`CAT=np`, 2,962 base entries), siglas and
foreign terms. The default missing-lemma list excludes those categories. They
remain available for diagnostics.

### Natura AO / pre-AO word lists

These two lists are used only to derive old-to-new spelling pairs for matching.
They are not definitions and are not presented as dictionary content. The
pipeline aligns the differing entries and requires a close string match before
recording a pair. The pairs are evidence for orthographic normalisation, not
proof of semantic identity.

### Wiktionary bridge snapshot

The sibling Lexi data is a KOReader-style dictionary compiled from the
Portuguese Wiktionary and the English Wiktionary (Portuguese entries) via
kaikki.org (wiktextract), with Lexi's own region marks (`BR`, `PT`), a small
approved PT-PT presentation layer and Lexi's unrevised automatic PT-PT
adaptation (which keeps the original wording in the record). Lexi2 uses it
only to give missing lemmas a labelled definition layer:

- matching is case-sensitive on the exact headword, first on the modern lemma
  and then on its recorded pre-AO spelling;
- every imported sense is flagged `wikt` in the runtime data and shown with an
  unreviewed notice; it is never merged into a Dicionário Aberto sense;
- the snapshot's explicit `BR` marks are preserved, and a conservative
  parenthetical-label scan (`(Brazil`, `(Brasil`) marks further senses;
  unmarked senses are not claimed to be European Portuguese;
- where the snapshot had applied its automatic PT-PT adaptation, the original
  wording is restored and the adapted text becomes a separately flagged
  suggestion, mirroring the Dicionário Aberto modernization model;
- capitalized headwords (proper nouns) and unknown part-of-speech labels are
  not imported.

The layer is third-party published content, not a Lexi2 editorial decision and
not human-reviewed. The counts are in `docs/CORPUS.md` under the Wiktionary
bridge layer.

## Licence compatibility

- Lexi2 code and generated database: GPL-3.0.
- Dicionário Aberto: CC BY-SA 2.5 PT, retained as source material with
  attribution. The generated database is distributed under GPL-3.0 with the
  Dicionário Aberto notice.
- words-pt: GPL-3.0.
- Hunspell pt_PT: GPL/LGPL/MPL; the build uses the GPL option.
- If interface material is copied from `../lexi` (CC BY-SA 4.0), it is
  redistributed under GPL-3.0 with attribution; CC BY-SA 4.0 is one-way
  compatible with GPLv3.
- The Wiktionary bridge senses (flagged `wikt`) come from the sibling Lexi
  snapshot (CC BY-SA 4.0, Wiktionary via kaikki.org) and are redistributed
  under GPL-3.0 with the attribution in `ATTRIBUTION.md`.

This is an engineering record, not legal advice. A redistribution review should
confirm the combined-work position before publication.
