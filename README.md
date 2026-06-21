# Quran Page Viewer

A Quran page-by-page viewer that uses QCF2 (Quran Complex Fonts V2) glyph fonts from quran.com's API. Includes a Python scraper, a static web viewer, and a protobuf exporter for Kotlin/Compose Multiplatform apps.

## How It Works

Each page of the Quran (604 total) has its own font file. Every word is a special glyph character rendered by the page-specific font. The scraper downloads verse data from the [quran.com API (v4)](https://api.quran.com) and font files from QuranCDN.

## Project Structure

```
quran_proj/
├── scraper.py           # Downloads verse/word data from quran.com API
├── download_fonts.py    # Downloads QCF2 TTF font files (threaded)
├── convert_to_pb.py     # Converts JSON to protobuf for Kotlin apps
├── index.html           # Web viewer
├── style.css            # Dark theme styles
├── app.js               # Viewer application logic
├── data/
│   ├── quran.json       # Generated: verse data (6236 verses)
│   └── quran.pb         # Generated: protobuf for Kotlin apps
├── fonts/               # Generated: woff2 + ttf fonts (p1-p604)
└── ttf_fonts/           # Generated: renamed TTF fonts (QCF_P001-P604)
```

## Setup

### 1. Scrape verse data

```bash
python3 scraper.py
```

Downloads all 604 pages of verse data from the quran.com API with a 2-second delay between requests. Saves to `data/quran.json`. Supports resuming if interrupted.

### 2. Download fonts

```bash
python3 download_fonts.py
```

Downloads 604 TTF font files using 10 parallel threads. Also downloads woff2 for web use during the scrape step.

### 3. Run the web viewer

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000` in your browser.

### 4. Export protobuf (for Kotlin/Compose Multiplatform)

```bash
python3 convert_to_pb.py
```

Generates `data/quran.pb` matching the `DecodedQuran`/`DecodedVerse` Kotlin schema.

## Data Format

### JSON (`data/quran.json`)

Flat array of 6236 verses:

```json
{
    "id": 1,
    "surah": 1,
    "juz": 1,
    "page": 1,
    "verse_num": 1,
    "word_count": 4,
    "text_glyphs": "ﱁ\tﱂ\tﱃ\tﱄ\tﱅ",
    "text": "بِسْمِ\tٱللَّهِ\tٱلرَّحْمَـٰنِ\tٱلرَّحِيمِ"
}
```

- `text_glyphs`: QCF2 glyph characters, **tab-separated** (some glyphs contain spaces). Last token is the verse number end marker.
- `text`: readable Arabic per word (uthmani script), **tab-separated**, aligned 1:1 with `text_glyphs`'s word tokens (i.e., excludes the end marker). Pause marks (ۛ ۖ) are bundled into the preceding word.
- `word_count`: number of word glyphs (excluding the end marker).

Invariants for every verse:
- `len(text.split("\t")) == word_count`
- `len(text_glyphs.split("\t")) - 1 == word_count`

### Protobuf (`data/quran.pb`)

Matches the Kotlin `DecodedQuran` schema:

- `text_glyphs` (field 7): tab-separated word glyphs → use `split("\t")` in Kotlin
- `verse_num_glyphs` (field 8): end marker glyph
- `text` (field 9): tab-separated readable Arabic per word, aligned 1:1 with field 7

### Fonts

- `fonts/p{N}.ttf` / `fonts/p{N}.woff2`: per-page QCF2 font files (1-604)
- `ttf_fonts/QCF_P{NNN}.ttf`: renamed TTF fonts with zero-padded page numbers

## Web Viewer Features

- Page-by-page navigation with sidebar (604 pages)
- QCF2 glyph font rendering matching the printed mushaf
- Word-level hover tooltips showing readable Arabic text
- Keyboard navigation (arrow keys)
- URL hash bookmarking (`#page=5`)
- Comparison split-view with quran.com iframe
- Dark theme

## API Sources

- Verse data: `https://api.quran.com/api/v4/verses/by_page/{page}?words=true&word_fields=code_v2,text_uthmani&per_page=all`
- TTF fonts: `https://static.qurancdn.com/fonts/quran/hafs/v2/ttf/p{page}.ttf`
- woff2 fonts: `https://static.qurancdn.com/fonts/quran/hafs/v2/woff2/p{page}.woff2`
