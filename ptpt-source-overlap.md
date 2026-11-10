# PT-PT source overlap report

Read-only audit, generated 2026-11-08. No dictionary shards, app files, service worker or version were changed.

Machine-readable companion: `ptpt-source-overlap.json`.

## Sources

| Source | What was used | Limits |
|---|---|---|
| Lexi corpus | `data/[a-z_].json`, 81,068 headwords | Wiktionary-derived, mixed PT-BR/PT-PT |
| Dicionário Aberto | Official SQL dump, 128,520 parsed entries, 152,395 senses | Cândido de Figueiredo, **1913**; CC BY-SA 2.5 Portugal |
| VOP | Public exact search and lemma pages | Spelling/morphological vocabulary; not a usage-frequency dictionary |

VOP was queried one form at a time, using exact search and the lemma page's regional label. No bulk crawl of VOP was performed.

## Method

1. Parsed the Dicionário Aberto `word` and `revision` tables from the official SQL dump.
2. Matched current headwords to Dicionário Aberto in three tiers: case-insensitive, accent-insensitive, and loose historical normalisation.
3. Applied candidate rules only to `unmarked` senses; quoted text was removed for the “unquoted” counts.
4. Queried VOP for every candidate original/replacement form and read the region label from the lemma page.
5. Classified a conversion as `PASS` only when the replacement is PT/unmarked and the original is BR/not found.

## Current corpus

| Measure | Count |
|---|---:|
| Headwords | 81,068 |
| Senses in shards | 133,763 |
| `meta.source_senses` (excludes curated additions) | 133,646 |
| `unmarked` senses | 130,343 |
| `BR`-marked senses | 2,648 |
| `PT`-marked senses | 655 |
| `curated` senses | 117 |

`meta.source_senses` is 117 lower than the actual shard total because it does not include the 117 curated senses.

## Dicionário Aberto overlap

Dicionário Aberto has **128,520 parsed entries** (metadata says 128,521) and **152,395 senses**. It is a real PT-PT dictionary, but it is a 1913 dictionary: old orthography, old vocabulary and old definitions.

| Match tier | Current headwords covered | Share |
|---|---:|---:|
| Exact, case-insensitive | 35,821 | 44.2% |
| Accent-insensitive | 37,671 | 46.5% |
| Loose historical normalisation | 38,525 | 47.5% |

“Loose” applies accent folding plus `ph→f`, `th→t`, `y→i`, `ll→l`, `mm→m`, `nn→n`, `ss→s`. It is an upper bound and can over-match.

### By headword type

| Type | Headwords | Accent-insensitive coverage |
|---|---:|---:|
| Single word | 69,613 | 37,612 (54.0%) |
| Multiword | 9,819 | 0 (0.0%) |
| Acronym | 1,050 | 55 (5.2%) |
| Affix | 499 | 0 exact; 280 loose |
| Other | 52 | 4 (7.7%) |
| Symbol | 35 | 0 |

The important result is that **Dicionário Aberto is essentially a single-word dictionary**. It does not solve the 9,819 multiword headwords, and it covers just over half of the current single-word lemmas.

### What it would add

- **88,754 unique accent-insensitive forms** exist in Dicionário Aberto but not in the current corpus.
- **22,123 of those (24.6%)** contain old-orthography markers.
- The rest include rare, archaic, regional and proper-name material. They should not be merged wholesale.
- A raw union would be about **167k unique normalised forms**, but that number is inflated by historical variants and is not a useful target size.

**Conclusion:** Dicionário Aberto is useful as a separate “PT-PT historical (1913)” layer for the ~37,671 overlapping headwords. It cannot replace the modern definition layer, and it does not help with multiword expressions.

## VOP gate

VOP is a spelling vocabulary. It explicitly labels some lemmas as `Brasil` or `Portugal`, but most lexical items are unmarked. “Exists in VOP” therefore does **not** mean “preferred in PT-PT”.

Example:

| Form | VOP label | Meaning |
|---|---|---|
| `gênero` | Brasil | Brazilian spelling |
| `género` | Portugal | Portuguese spelling |
| `suco` | unmarked | exists, but VOP does not say it is Brazilian |
| `sumo` | unmarked | exists, but VOP does not rank it above `suco` |

### Orthographic pass

These 12 rules target explicit spelling variants. All 12 pass the VOP gate.

| Rule | Unmarked senses | VOP original | VOP replacement |
|---|---:|---|---|
| `gênero(s)` → `género(s)` | 642 | BR | PT |
| `fenômeno(s)` → `fenómeno(s)` | 173 | BR | PT |
| `econômic-` → `económic-` | 130 | BR | PT |
| `homônim-` → `homónim-` | 73 | BR | PT |
| `tônic-` → `tónic-` | 31 | BR | PT |
| `sinônim-` → `sinónim-` | 18 | BR | PT |
| `antônim-` → `antónim-` | 5 | BR | PT |
| `cômic-` → `cómic-` | 13 | BR | PT |
| `eletrônic-` → `eletrónic-` | 0 remaining | BR | PT |
| `contato(s)` → `contacto(s)` | 109 | BR | unmarked |
| `planejamento(s)` → `planeamento(s)` | 13 | BR | unmarked |
| `planejar` → `planear` | 20 | BR | unmarked |

**Total: 1,227 unmarked senses (1,259 occurrences)** after excluding quoted text. This is the only set that can be applied automatically with VOP support, and even this should be stored as an unreviewed suggestion with the original text preserved.

`planejar` matches only the infinitive in this pass. Inflected forms (`planeja`, `planejou`, `planejando`, etc.) need a conjugation-aware rule and are not included in the 1,227.

### Orthographic rules that fail the gate

| Rule | Unmarked senses | Why |
|---|---:|---|
| `registro(s)` → `registo(s)` | 82 | VOP has both as valid; not a clear regional spelling rule |
| `fôrma(s)` → `forma(s)` | 1 | both unmarked; the difference is semantic |
| `planejado(s)` → `planeado(s)` | 0 remaining | both unmarked |

**Total: 83 senses that must not be auto-applied.**

### Lexical watch-list

The lexical list matched **629 unmarked senses (659 occurrences)**. This is not a conversion estimate: it is an occurrence count, and some rules are deliberately included to show why a blind pass is unsafe.

| Rule | Unmarked senses | VOP evidence | Verdict |
|---|---:|---|---|
| `caminhão/ões` → `camião/ões` | 13 | BR → unmarked | form passes; sense is clear |
| `tênis` → `sapatilhas` | 11 | BR → unmarked | form passes; football/tennis sense needs context |
| `carona(s)` → `boleia(s)` | 5 | BR → unmarked | form passes |
| `mamadeira(s)` → `biberão/ões` | 1 | BR → unmarked | form passes |
| `café da manhã` → `pequeno-almoço` | 8 | not in VOP → unmarked | form passes; multiword source |
| `tela(s)` → `ecrã(s)` | 53 | both unmarked | not gated |
| `celular(es)` → `telemóvel/éis` | 61 | both unmarked | not gated |
| `arquivo(s)` → `ficheiro(s)` | 51 | both unmarked | not gated |
| `time(s)` → `equipa(s)` | 36 | both unmarked | not gated; English loan sense |
| `camisa(s)` → `camisola(s)` | 26 | both unmarked | not gated; `camisa` is valid PT for shirt |
| `biscoito(s)` → `bolacha(s)` | 21 | both unmarked | not gated |
| `sorvete(s)` → `gelado(s)` | 12 | both unmarked | not gated |
| `abacaxi(s)` → `ananás` | 8 | both unmarked | not gated |
| `torcida(s)` → `claque(s)` | 8 | both unmarked | not gated; `torcida` also means twisted |
| `trem(ns)` → `comboio(s)` | 22 | both unmarked | not gated; many non-rail senses |
| `açougue(s)` → `talho(s)` | 6 | both unmarked | not gated |
| `fato(s)` → `facto(s)` | 287 | both unmarked | **not a valid rule**; most matches are not the “fact” sense |

Rules with zero remaining matches (`ônibus`, `usuário`, `aplicativo`, `suco`, `banheiro`, `xícara`, `geladeira`, `grampeador`) are omitted from this table. The 629 total is the sum of all lexical rules, including the zero-match entries.

The headline is that VOP validates **spelling**, not **lexical preference**. `suco`, `geladeira`, `celular`, `tela`, `banheiro`, `xícara`, `sorvete`, `abacaxi`, `biscoito`, `camisa`, `torcida`, `arquivo`, `time` and `trem` are all unmarked in VOP. The existing regional table is an editorial resource, not something VOP can confirm.

## Existing v7 substitutions

The v7 audit records 339 automatic substitutions.

| v7 rule | Count | VOP status |
|---|---:|---|
| `eletrônico` | 121 | Pass (BR → PT) |
| `ônibus` | 34 | Pass (BR → unmarked) |
| `usuário` | 50 | Ambiguous (both unmarked) |
| `suco` | 46 | Ambiguous |
| `tela informática` | 24 | Ambiguous |
| `aplicativo` | 20 | Ambiguous |
| `planejado` | 17 | Ambiguous |
| `banheiro` | 10 | Multiword, not in VOP |
| `telefone celular` | 9 | Ambiguous |
| `xícara` | 5 | Ambiguous |
| `geladeira` | 3 | Ambiguous |

| Result | Count | Share |
|---|---:|---:|
| VOP-safe | 155 | 45.7% |
| VOP-ambiguous | 174 | 51.3% |
| Multiword/not in VOP | 10 | 2.9% |

Only `eletrônico` and `ônibus` are confirmed spelling/regional substitutions. More than half of the v7 edits were lexical choices that VOP cannot validate. This does not make them wrong, but it means they need contextual review rather than being presented as spelling corrections.

## Regional table

`data/regional.json` has 57 terms.

| Result | Count |
|---|---:|
| PT form exists in VOP | 49 |
| Multiword form outside VOP scope | 8 |
| Single-word failure | 0 |

The 8 out-of-scope forms are `casa de banho`, `paragem de autocarro`, `autocarro escolar`, `autocarro de turismo`, and their reverse equivalents. VOP does not list multiword expressions; this is a scope limitation, not evidence that they are wrong.

## Recommendations

1. **Apply the 12 orthographic rules only as suggestions.** They cover 1,227 unmarked senses. Preserve the original text and keep the unreviewed label.
2. **Do not auto-apply `registro`, `fôrma` or `planejado`.** VOP has both forms as valid; the choice is semantic or usage-dependent.
3. **Do not treat the lexical VOP results as validation.** Lexical adaptation needs sense-level context rules or editorial review. `fato` is the clearest warning: 287 raw matches, almost none of them a valid “fact” conversion.
4. **Add Dicionário Aberto as a separate historical layer**, not as a replacement. It overlaps 37,671 headwords, but it is 1913 material and does not cover multiword expressions.
5. **Do not merge the 88,754 Dicionário Aberto-only forms wholesale.** 22,123 contain old-orthography markers, and the rest include rare/archaic material.
6. **Keep the 57-term regional table.** Its PT forms are mostly present in VOP; the 8 multiword forms are outside VOP scope.
7. **For modern PT-PT definitions at scale, license a modern dictionary or expand curated entries.** No open, modern, comprehensive PT-PT dictionary replacement was found.

## Limits

- Headword matching is case- and accent-insensitive; it does not align senses or meanings.
- Dicionário Aberto is a 1913 dictionary, not contemporary PT-PT.
- VOP is a spelling vocabulary, not a usage-frequency corpus.
- Candidate counts are occurrences in `unmarked` senses, not reviewed conversions.
- Quoted text was excluded from the quoted counts; proper nouns and examples were not separately removed.
- No runtime changes were made.
