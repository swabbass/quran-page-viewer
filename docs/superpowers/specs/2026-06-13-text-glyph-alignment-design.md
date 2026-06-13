# Per-Word Text Aligned to Glyphs

## Problem

In `data/quran.json`, each verse has:
- `code`: tab-separated QCF2 glyphs, last glyph is the end marker
- `text`: space-joined readable Arabic (uthmani script)

`code` is correctly aligned with `word_count` (verified: 0 mismatches across 6236 verses). But `text.split(" ")` produces a different token count than `code.split("\t")` in **2,720 of 6236 verses (~44%)**.

Root cause is in `scraper.py:182-191`: pause marks (ۛ ۖ) arrive from the API as `char_type_name == "word"` entries with a `text_uthmani` but no `code_v2`. The current loop appends to `words_text` whenever `text_uthmani` exists but only appends to `word_glyphs` when `code_v2` exists, so the two arrays drift apart.

Today this also produces wrong tooltips in `app.js:189-201`, which pairs `text.split(" ")[i]` with `code.split("\t")[i]`.

## Goal

Per-word readable Arabic text aligned 1:1 with each word glyph, available in JSON, the protobuf, and rendered as a small label above each glyph in the web viewer.

## Design

### Data layer (scraper.py)

Pair text and glyphs strictly in the phase-2 word loop. Only append `text_uthmani` when the same word also contributes a `code_v2` glyph. Emit a new field:

- `text_glyphs` (string, tab-separated, aligned 1:1 with non-end glyphs of `code`)

Invariants (post-fix, for every verse):
- `len(text_glyphs.split("\t")) == word_count`
- `len(code.split("\t")) - 1 == word_count`

Keep existing `text` field (space-joined readable verse) unchanged for backward compat. All raw API responses are already cached locally under `data/raw/page_*.json` — re-process only, no re-download.

### Protobuf (convert_to_pb.py)

Add field 9 to `DecodedVerse`:

```
9: text_glyphs (string, tab-separated)
```

Field numbers 1–8 keep their meaning. Kotlin `DecodedVerse` schema documented in README will need the parallel field on the consumer side.

### Verifier (verify.py)

Extend `check_pb_against_json` to also compare field 9. Add a local invariant pass: every verse must satisfy both length invariants above. Run with `python3 verify.py pb`.

### UI (index.html / style.css / app.js)

- Each rendered word becomes a stacked element: a small readable Arabic label (normal font) on top, the QCF2 glyph below. Implementation: nested `<small>` element inside each `.quran-word` span.
- Header toggle button (`إظهار النص` / `إخفاء النص`), default off. Toggles `.show-text` class on `#page-lines`; CSS shows/hides the `<small>` label.
- Switch tooltip source from `verse.text.split(" ")` to `verse.text_glyphs.split("\t")` — fixes 2,720 broken tooltips as a side effect.
- End marker has no readable text.

### Documentation

Update README Data Format section (JSON and protobuf) to document `text_glyphs` and the alignment invariants.

## Out of scope

- Kotlin consumer-side changes (mentioned in README only)
- Removing or repurposing the existing `text` field
- Translations or per-word transliteration

## Implementation order

1. Patch `scraper.py` phase-2 word loop — pair text/code, emit `text_glyphs`
2. Re-process from `data/raw/` → regenerate `data/quran.json`
3. Patch `convert_to_pb.py` — add field 9
4. Regenerate `data/quran.pb`
5. Patch `verify.py pb` — check field 9 + invariants; run
6. Patch `index.html` + `style.css` + `app.js` — toggle button, stacked layout, fix tooltip source
7. Update README Data Format section
