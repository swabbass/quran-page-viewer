#!/usr/bin/env python3
"""
Download QCF2 TTF font files (604 pages) using parallel threads.
"""

import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
FONT_BASE = "https://static.qurancdn.com/fonts/quran/hafs/v2/ttf"
TOTAL_PAGES = 604
MAX_WORKERS = 10


def download_font(page_num):
    font_path = os.path.join(FONTS_DIR, f"p{page_num}.ttf")
    if os.path.exists(font_path) and os.path.getsize(font_path) > 0:
        return page_num, True, "cached"
    url = f"{FONT_BASE}/p{page_num}.ttf"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QuranPageViewer/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(font_path, "wb") as f:
                f.write(resp.read())
        return page_num, True, "downloaded"
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        return page_num, False, str(e)


def main():
    os.makedirs(FONTS_DIR, exist_ok=True)

    # Check how many already exist
    existing = sum(
        1 for p in range(1, TOTAL_PAGES + 1)
        if os.path.exists(os.path.join(FONTS_DIR, f"p{p}.ttf"))
        and os.path.getsize(os.path.join(FONTS_DIR, f"p{p}.ttf")) > 0
    )
    print(f"TTF fonts: {existing}/{TOTAL_PAGES} already downloaded")

    pages_to_download = [
        p for p in range(1, TOTAL_PAGES + 1)
        if not os.path.exists(os.path.join(FONTS_DIR, f"p{p}.ttf"))
        or os.path.getsize(os.path.join(FONTS_DIR, f"p{p}.ttf")) == 0
    ]

    if not pages_to_download:
        print("All TTF fonts already downloaded!")
        return

    print(f"Downloading {len(pages_to_download)} TTF fonts with {MAX_WORKERS} threads...")

    done = 0
    failed = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_font, p): p for p in pages_to_download}
        for future in as_completed(futures):
            page_num, success, msg = future.result()
            done += 1
            if not success:
                failed.append(page_num)
                print(f"  FAILED p{page_num}: {msg}")
            if done % 50 == 0 or done == len(pages_to_download):
                print(f"  {done}/{len(pages_to_download)} done")

    if failed:
        print(f"\n{len(failed)} failed: {sorted(failed)}")
        print("Re-run to retry failed downloads.")
    else:
        print(f"\nDone! All {TOTAL_PAGES} TTF fonts downloaded.")


if __name__ == "__main__":
    main()
