#!/usr/bin/env python3
"""
Quran Page Viewer - Data Scraper
Downloads verse data and V2 glyph fonts from quran.com API (v4).

Two-phase approach:
  Phase 1: Download all 604 API pages (parallel) and save raw JSON responses.
  Phase 2: Process all responses — group words by page_number, build output.
"""

import json
import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
RAW_DIR = os.path.join(DATA_DIR, "raw")
OUTPUT_FILE = os.path.join(DATA_DIR, "quran.json")

API_BASE = "https://api.quran.com/api/v4"
FONT_BASE = "https://static.qurancdn.com/fonts/quran/hafs/v2/woff2"

TOTAL_PAGES = 604
MAX_WORKERS = 8
DELAY_BETWEEN_BATCHES = 1


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FONTS_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)


def fetch_url(url, headers=None, timeout=30):
    hdrs = headers or {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QuranPageViewer/1.0",
    }
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_font(page_num):
    font_path = os.path.join(FONTS_DIR, f"p{page_num}.woff2")
    if os.path.exists(font_path) and os.path.getsize(font_path) > 0:
        return page_num, True
    url = f"{FONT_BASE}/p{page_num}.woff2"
    data = fetch_url(url)
    with open(font_path, "wb") as f:
        f.write(data)
    return page_num, True


def download_page_json(page_num):
    raw_path = os.path.join(RAW_DIR, f"page_{page_num}.json")
    if os.path.exists(raw_path) and os.path.getsize(raw_path) > 0:
        return page_num, True
    url = (
        f"{API_BASE}/verses/by_page/{page_num}"
        f"?words=true&word_fields=code_v2,text_uthmani&per_page=all"
    )
    data = fetch_url(url)
    with open(raw_path, "wb") as f:
        f.write(data)
    return page_num, True


def download_all():
    """Phase 1: Download all fonts and API pages in parallel."""
    print("=== Phase 1: Downloading ===")

    # Find what's already downloaded
    pages_needed = []
    fonts_needed = []
    for p in range(1, TOTAL_PAGES + 1):
        raw_path = os.path.join(RAW_DIR, f"page_{p}.json")
        if not (os.path.exists(raw_path) and os.path.getsize(raw_path) > 0):
            pages_needed.append(p)
        font_path = os.path.join(FONTS_DIR, f"p{p}.woff2")
        if not (os.path.exists(font_path) and os.path.getsize(font_path) > 0):
            fonts_needed.append(p)

    total = len(pages_needed) + len(fonts_needed)
    if total == 0:
        print("All files already downloaded!")
        return True

    print(f"Need to download: {len(pages_needed)} API pages, {len(fonts_needed)} fonts")
    done = 0
    errors = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {}
        for p in pages_needed:
            futures[pool.submit(download_page_json, p)] = ("page", p)
        for p in fonts_needed:
            futures[pool.submit(download_font, p)] = ("font", p)

        for future in as_completed(futures):
            kind, page_num = futures[future]
            done += 1
            try:
                future.result()
                if done % 50 == 0 or done == total:
                    print(f"  {done}/{total} downloaded")
            except Exception as e:
                errors.append((kind, page_num, str(e)))
                print(f"  Error {kind} {page_num}: {e}")

    if errors:
        print(f"\n{len(errors)} errors. Re-run to retry.")
        return False

    print(f"All {total} files downloaded successfully!")
    return True


def process_all():
    """Phase 2: Process raw JSON files and build quran.json.

    Groups words by their page_number field, so each verse's words
    end up on the correct page regardless of which API endpoint returned them.
    """
    print("\n=== Phase 2: Processing ===")

    # Collect all words grouped by (page_number, verse_key)
    # Structure: page_num -> verse_key -> { meta, words[] }
    page_verses = {}

    for api_page in range(1, TOTAL_PAGES + 1):
        raw_path = os.path.join(RAW_DIR, f"page_{api_page}.json")
        if not os.path.exists(raw_path):
            print(f"  Missing raw data for page {api_page}!")
            return

        with open(raw_path, "r") as f:
            resp = json.load(f)

        for v in resp["verses"]:
            verse_key = v["verse_key"]
            surah_num = int(verse_key.split(":")[0])
            meta = {
                "surah": surah_num,
                "juz": v.get("juz_number", 1),
                "verse_num": v["verse_number"],
            }

            for w in v["words"]:
                wpn = w.get("page_number", api_page)

                if wpn not in page_verses:
                    page_verses[wpn] = {}
                if verse_key not in page_verses[wpn]:
                    page_verses[wpn][verse_key] = {"meta": meta, "words": []}

                # Avoid duplicate words (same verse returned by multiple API pages)
                word_id = w.get("id")
                existing_ids = {ew.get("id") for ew in page_verses[wpn][verse_key]["words"]}
                if word_id not in existing_ids:
                    page_verses[wpn][verse_key]["words"].append(w)

    # Build output sorted by page, then by verse order
    data = []
    next_id = 1

    for page_num in sorted(page_verses.keys()):
        verse_map = page_verses[page_num]
        for verse_key in sorted(verse_map, key=lambda k: (int(k.split(":")[0]), int(k.split(":")[1]))):
            info = verse_map[verse_key]
            meta = info["meta"]
            # Sort words by position to maintain order
            words = sorted(info["words"], key=lambda w: w.get("position", 0))

            text_per_glyph = []   # readable Arabic word, aligned 1:1 with word_glyphs
            word_glyphs = []
            end_glyph = ""
            for w in words:
                code = w.get("code_v2", "")
                char_type = w.get("char_type_name", "word")
                if char_type == "end":
                    end_glyph = code
                elif char_type == "word" and code:
                    # Only pair text with words that contribute a glyph.
                    # Pause marks (ۛ ۖ) arrive as "word" entries with text_uthmani
                    # but no code_v2 — drop them so text and glyphs stay aligned.
                    word_glyphs.append(code)
                    text_per_glyph.append(w.get("text_uthmani", ""))

            if not word_glyphs and not end_glyph:
                continue

            all_glyphs = word_glyphs + ([end_glyph] if end_glyph else [])
            data.append({
                "id": next_id,
                "surah": meta["surah"],
                "juz": meta["juz"],
                "page": page_num,
                "verse_num": meta["verse_num"],
                "word_count": len(word_glyphs),
                "text_glyphs": "\t".join(all_glyphs),
                "text": "\t".join(text_per_glyph),
            })
            next_id += 1

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Stats
    unique_verses = set((v["surah"], v["verse_num"]) for v in data)
    print(f"  Total entries: {len(data)}")
    print(f"  Unique verses: {len(unique_verses)}")
    print(f"  Pages covered: {len(page_verses)}")
    print(f"\nDone! Written to {OUTPUT_FILE}")


def main():
    ensure_dirs()
    if download_all():
        process_all()


if __name__ == "__main__":
    main()
