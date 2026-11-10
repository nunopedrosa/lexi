# Attribution and licences

Lexi2 is distributed under the **GNU General Public License, version 3**
(`GPL-3.0`). The generated dictionary database is part of the same distribution
and is also released under GPL-3.0, with the source-specific attribution below.

This project combines material with different licences. The notices must remain
with any redistributed source snapshots, generated data and application files.

## Dicionário Aberto

- Source: <https://github.com/ambs/Dicionario-Aberto> and
  <https://dicionario-aberto.net/>
- Snapshot used: `SQL/data-20151213.sql.xz`
- Licence: **Creative Commons Attribution-ShareAlike 2.5 Portugal**
  (<https://creativecommons.org/licenses/by-sa/2.5/pt/>)
- Attribution: Dicionário Aberto, maintained by Alberto Simões and contributors,
  based on Cândido de Figueiredo's *Novo Dicionário da Língua Portuguesa*
  (1913). The original dictionary text and the database transcription remain
  subject to the Dicionário Aberto licence and attribution.
- Changes: Lexi2 extracts entries and senses, adds matching metadata, automatic
  spelling-modernisation suggestions and review flags. The original definition
  text is preserved. These changes are identified in the generated records and
  in `docs/CORPUS.md`.

## words-pt

- Source: <https://github.com/jfoclpf/words-pt>
- Snapshot used: `wordsList.zip` (word list dated 2020-03-02)
- Licence: **GNU General Public License, version 3** (`GPL-3.0`)
- Attribution: words-pt by João Pedro Ferreira and contributors, based on the
  word lists produced by the Departamento de Informática, Universidade do Minho
  (Natura).
- Changes: Lexi2 uses the list as a form inventory and cross-checks it against
  the Dicionário Aberto and the Hunspell pt_PT lemma data. The generated
  dictionary is distributed under GPL-3.0.

## Hunspell pt_PT

- Source: <https://natura.di.uminho.pt/download/sources/Dictionaries/hunspell/>
- Snapshot used: `hunspell-pt_PT-20251001.tar.gz`
- Licence: **GPL / LGPL / MPL**, by that order (see the source `COPYING` file).
- Attribution: Hunspell Portuguese (Portugal) dictionary, Departamento de
  Informática, Universidade do Minho.
- Changes: Lexi2 reads lemma entries, explicit inflected forms and `PREAO90`
  spelling metadata to build the lemma and form indexes. No Hunspell runtime
  code is included in the PWA.

## Lexi presentation layer

If any interface code, artwork or documentation is copied from the sibling
`../lexi` project:

- Source: Lexi, <https://lexi.basecentral.link/>
- Licence: **Creative Commons Attribution-ShareAlike 4.0 International**
  (`CC-BY-SA-4.0`)
- Compatibility: CC BY-SA 4.0 is one-way compatible with GPLv3. The copied
  material is redistributed here under GPL-3.0 with attribution.
- Changes: The data model and corpus are replaced. Lexi's original dictionary
  corpus and editorial claims do not apply to Lexi2.

## Wiktionary bridge layer

A labelled, unreviewed definition layer for lemmas that have no Dicionário
Aberto entry is built from the dictionary snapshot compiled in the sibling
Lexi project:

- Source: Portuguese Wiktionary and English Wiktionary (Portuguese entries),
  extracted with wiktexport and distributed via
  [kaikki.org](https://kaikki.org/); compiled into the Lexi dictionary data
  (sibling `../lexi` project, data snapshot pinned in `docs/SOURCES.md`).
- Licence: **Creative Commons Attribution-ShareAlike 4.0 International**
  (`CC-BY-SA-4.0`), as applied to the Wiktionary text by its contributors.
- Attribution: Wiktionary contributors; dictionary definitions extracted via
  wiktextract (kaikki.org) and compiled by the Lexi project.
- Compatibility: CC BY-SA 4.0 is one-way compatible with GPLv3; the layer is
  redistributed here as part of the GPL-3.0 dictionary database with this
  attribution.
- Changes: Lexi2 matches the snapshot headwords against its missing-lemma
  list, restores the original wording where the snapshot had applied its own
  unrevised automatic PT-PT adaptation (the adapted wording is kept as a
  separately flagged suggestion), preserves the snapshot's explicit
  Brazilian labels and adds a conservative parenthetical-label scan. Senses
  are flagged `wikt` in the runtime data, shown with an unreviewed notice and
  never merged into the Dicionário Aberto text. The layer is not
  human-reviewed lexicography.

## Curated PT-PT / PT-BR correspondence table

`sources/regional-ptpt-br.json` is a small, sense-dependent correspondence table
carried over from the Lexi project and curated by the project owner. It is not a
global translation and does not replace the Dicionário Aberto definitions. It is
used only to point out a European Portuguese equivalent or a Brazilian usage for
the specific sense named in the table.

## Required notices

When redistributing Lexi2 or generated data:

1. Keep this file, `LICENSE` and the source notices.
2. Keep the Dicionário Aberto attribution and CC BY-SA 2.5 PT notice with the
   dictionary data.
3. Keep the words-pt and Hunspell pt_PT attributions.
4. Keep the Wiktionary attribution for the senses flagged `wikt`.
5. Do not present the automatic modernisation, the Wiktionary bridge layer or
   the review flags as human-reviewed lexicography.

## No warranty

The sources are historical and may contain obsolete, regional, archaic or
incorrect material. Lexi2 preserves the source text and labels uncertainty; it
does not guarantee that a definition is current or suitable for a particular
purpose.
