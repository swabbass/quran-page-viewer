#!/usr/bin/env python3
"""
Quran Page Viewer - Data Scraper
Downloads verse data and V2 glyph fonts from quran.com API (v4).
Supports resuming interrupted downloads.
"""

import json
import os
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
OUTPUT_FILE = os.path.join(DATA_DIR, "quran.json")
PROGRESS_FILE = os.path.join(DATA_DIR, ".progress.json")

API_BASE = "https://api.quran.com/api/v4"
FONT_BASE = "https://static.qurancdn.com/fonts/quran/hafs/v2/woff2"

TOTAL_PAGES = 604
DELAY_SECONDS = 2


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FONTS_DIR, exist_ok=True)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"completed_pages": [], "next_id": 1}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def load_existing_data():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    return []


def save_data(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QuranPageViewer/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_font(page_num):
    font_path = os.path.join(FONTS_DIR, f"p{page_num}.woff2")
    if os.path.exists(font_path) and os.path.getsize(font_path) > 0:
        return
    url = f"{FONT_BASE}/p{page_num}.woff2"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QuranPageViewer/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        with open(font_path, "wb") as f:
            f.write(resp.read())


def fetch_page(page_num, next_id):
    url = (
        f"{API_BASE}/verses/by_page/{page_num}"
        f"?words=true&word_fields=code_v2,text_uthmani&per_page=all"
    )
    resp = fetch_json(url)
    verses = []
    for v in resp["verses"]:
        words_text = []
        word_glyphs = []
        end_glyph = ""
        for w in v["words"]:
            code = w.get("code_v2", "")
            char_type = w.get("char_type_name", "word")
            if char_type == "end":
                end_glyph = code
            elif char_type == "word":
                if code:
                    word_glyphs.append(code)
                if w.get("text_uthmani"):
                    words_text.append(w["text_uthmani"])
        surah_num = int(v["verse_key"].split(":")[0])
        # Use tab separator - code_v2 values can contain spaces
        all_glyphs = word_glyphs + ([end_glyph] if end_glyph else [])
        verses.append({
            "id": next_id,
            "surah": surah_num,
            "juz": v.get("juz_number", 1),
            "page": page_num,
            "verse_num": v["verse_number"],
            "word_count": len(word_glyphs),
            "text": " ".join(words_text),
            "code": "\t".join(all_glyphs),
        })
        next_id += 1
    return verses, next_id


def main():
    ensure_dirs()
    progress = load_progress()
    data = load_existing_data()

    completed = set(progress["completed_pages"])
    next_id = progress["next_id"]
    remaining = [p for p in range(1, TOTAL_PAGES + 1) if p not in completed]

    if not remaining:
        print("All pages already downloaded!")
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        return

    print(f"Resuming from page {remaining[0]} ({len(completed)} already done)")

    for page_num in remaining:
        try:
            print(f"Page {page_num}/{TOTAL_PAGES}...", end=" ", flush=True)

            # Download font
            download_font(page_num)
            print("font", end=" ", flush=True)

            # Fetch verse data
            verses, next_id = fetch_page(page_num, next_id)
            data.extend(verses)
            print(f"data ({len(verses)} verses)")

            # Save incrementally
            completed.add(page_num)
            progress["completed_pages"] = sorted(completed)
            progress["next_id"] = next_id
            save_data(data)
            save_progress(progress)

            if page_num != remaining[-1]:
                time.sleep(DELAY_SECONDS)

        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            print(f"\nError on page {page_num}: {e}")
            print("Progress saved. Re-run to resume.")
            save_data(data)
            save_progress(progress)
            return
        except KeyboardInterrupt:
            print(f"\nInterrupted at page {page_num}. Progress saved. Re-run to resume.")
            save_data(data)
            save_progress(progress)
            return

    print(f"\nDone! All {TOTAL_PAGES} pages downloaded. {len(data)} verses total.")
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    main()
