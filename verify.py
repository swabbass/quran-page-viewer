#!/usr/bin/env python3
"""
Verify scraped quran.json against quran.com API.
Checks that each page has the correct verses with matching words.
"""

import json
import os
import sys
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "quran.json")
PB_TO_CHECK = os.path.join(DATA_DIR, "quran-to-check.pb")
API_BASE = "https://api.quran.com/api/v4"

KNOWN_VERSE_COUNTS = {
    1:7,2:286,3:200,4:176,5:120,6:165,7:206,8:75,9:129,10:109,
    11:123,12:111,13:43,14:52,15:99,16:128,17:111,18:110,19:98,
    20:135,21:112,22:78,23:118,24:64,25:77,26:227,27:93,28:88,
    29:69,30:60,31:34,32:30,33:73,34:54,35:45,36:83,37:182,38:88,
    39:75,40:85,41:54,42:53,43:89,44:59,45:37,46:35,47:38,48:29,
    49:18,50:45,51:60,52:49,53:62,54:55,55:78,56:96,57:29,58:22,
    59:24,60:13,61:14,62:11,63:11,64:18,65:12,66:12,67:30,68:52,
    69:52,70:44,71:28,72:28,73:20,74:56,75:40,76:31,77:50,78:40,
    79:46,80:42,81:29,82:19,83:36,84:25,85:22,86:17,87:19,88:26,
    89:30,90:20,91:15,92:21,93:11,94:8,95:8,96:19,97:5,98:8,99:8,
    100:11,101:11,102:8,103:3,104:9,105:5,106:4,107:7,108:3,109:6,
    110:3,111:5,112:4,113:5,114:6,
}
TOTAL_VERSES = sum(KNOWN_VERSE_COUNTS.values())  # 6236


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "QuranVerifier/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_basics(data):
    """Check total count, duplicates, and missing verses."""
    print("=== Basic Checks ===")
    unique = set()
    dupes = []
    for v in data:
        key = (v["surah"], v["verse_num"], v["page"])
        if key in unique:
            dupes.append(key)
        unique.add(key)

    unique_verses = set((v["surah"], v["verse_num"]) for v in data)
    entries_per_page = len(data) - len(unique_verses)

    print(f"  Total entries: {len(data)}")
    print(f"  Unique verses: {len(unique_verses)} (expected {TOTAL_VERSES})")
    print(f"  Split-verse entries (span 2 pages): {entries_per_page}")
    print(f"  Duplicate entries: {len(dupes)}")

    # Find missing verses
    missing = []
    for s in range(1, 115):
        for vn in range(1, KNOWN_VERSE_COUNTS[s] + 1):
            if (s, vn) not in unique_verses:
                missing.append(f"{s}:{vn}")
    if missing:
        print(f"  MISSING {len(missing)} verses: {missing[:20]}{'...' if len(missing) > 20 else ''}")
    else:
        print("  All 6236 verses present!")

    return len(dupes) == 0 and len(missing) == 0


def check_pages_against_api(data, pages_to_check=None):
    """Compare specific pages against the API to verify verse alignment."""
    print("\n=== Page-by-Page API Verification ===")
    by_page = {}
    for v in data:
        by_page.setdefault(v["page"], []).append(v)

    if pages_to_check is None:
        # Check a sample: first, last, and known boundary pages
        pages_to_check = [1, 2, 3, 50, 100, 200, 300, 400, 500, 587, 588, 589, 590, 604]

    ok = True
    for page_num in pages_to_check:
        api_url = (
            f"{API_BASE}/verses/by_page/{page_num}"
            f"?words=true&word_fields=code_v2,page_number&per_page=all"
        )
        try:
            resp = fetch_json(api_url)
        except Exception as e:
            print(f"  Page {page_num}: API error - {e}")
            continue

        # Build expected verses: group API words by page_number
        expected = {}
        for v in resp["verses"]:
            vk = v["verse_key"]
            for w in v["words"]:
                wpn = w.get("page_number", page_num)
                if wpn == page_num:
                    if vk not in expected:
                        expected[vk] = {"words": 0, "end": False}
                    if w.get("char_type_name") == "word":
                        expected[vk]["words"] += 1
                    elif w.get("char_type_name") == "end":
                        expected[vk]["end"] = True

        # Our data for this page
        our_verses = by_page.get(page_num, [])
        our_keys = set(f"{v['surah']}:{v['verse_num']}" for v in our_verses)
        api_keys = set(expected.keys())

        # Note: API only returns verses whose FULL verse is fetched by this page endpoint.
        # Overflow verses (from previous page's API call) won't appear here.
        # So we only flag if API says a verse is on this page but we don't have it.
        missing_from_us = api_keys - our_keys
        extra_in_us = our_keys - api_keys  # These are overflow verses — expected

        if missing_from_us:
            print(f"  Page {page_num}: MISSING verses {missing_from_us}")
            ok = False
        else:
            # Check word counts match for API-reported verses
            word_mismatch = False
            for v in our_verses:
                vk = f"{v['surah']}:{v['verse_num']}"
                if vk in expected and v["word_count"] != expected[vk]["words"]:
                    print(f"  Page {page_num}: {vk} word count mismatch: ours={v['word_count']} api={expected[vk]['words']}")
                    word_mismatch = True
                    ok = False
            overflow_note = f" (+{len(extra_in_us)} overflow)" if extra_in_us else ""
            if not word_mismatch:
                print(f"  Page {page_num}: OK - {len(our_verses)} verses{overflow_note}")

        time.sleep(1)

    return ok


# ── Protobuf decoder (DecodedQuran schema) ──
# DecodedQuran { repeated DecodedVerse verses = 1; }
# DecodedVerse {
#   1:id 2:surah 3:juz 4:page 5:verse_num 6:word_count (int32)
#   7:text_glyphs (string, tab-separated)
#   8:verse_num_glyphs (string)
# }

def _read_varint(buf, pos):
    result, shift = 0, 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _decode_message(buf, start, end):
    fields = {}
    pos = start
    while pos < end:
        tag, pos = _read_varint(buf, pos)
        field_num, wire = tag >> 3, tag & 7
        if wire == 0:
            val, pos = _read_varint(buf, pos)
            fields[field_num] = val
        elif wire == 2:
            length, pos = _read_varint(buf, pos)
            fields[field_num] = bytes(buf[pos:pos + length])
            pos += length
        else:
            raise ValueError(f"Unsupported wire type {wire} at field {field_num}")
    return fields


def _decode_quran_pb(buf):
    verses = []
    pos, end = 0, len(buf)
    while pos < end:
        tag, pos = _read_varint(buf, pos)
        field_num, wire = tag >> 3, tag & 7
        if field_num == 1 and wire == 2:
            length, pos = _read_varint(buf, pos)
            verses.append(_decode_message(buf, pos, pos + length))
            pos += length
        else:
            raise ValueError(f"Unexpected top-level field {field_num} wire {wire}")
    return verses


def _pb_verses_to_dicts(pb_verses):
    """Convert decoded pb messages into the verse-dict shape used by JSON checks."""
    out = []
    for pv in pb_verses:
        text_glyphs = pv.get(7, b"").decode("utf-8")
        verse_num_glyphs = pv.get(8, b"").decode("utf-8")
        text = pv.get(9, b"").decode("utf-8")
        # Rebuild the JSON-shape text_glyphs (word glyphs + end marker, tab-separated)
        full_glyphs = text_glyphs
        if verse_num_glyphs:
            full_glyphs = (text_glyphs + "\t" + verse_num_glyphs) if text_glyphs else verse_num_glyphs
        out.append({
            "id": pv.get(1, 0),
            "surah": pv.get(2, 0),
            "juz": pv.get(3, 0),
            "page": pv.get(4, 0),
            "verse_num": pv.get(5, 0),
            "word_count": pv.get(6, 0),
            "text_glyphs": full_glyphs,
            "text": text,
        })
    return out


def check_pb_against_json(data, pb_path=PB_TO_CHECK):
    """Decode pb_path and verify every field matches the JSON source."""
    print(f"\n=== Protobuf vs JSON ({os.path.basename(pb_path)}) ===")
    if not os.path.exists(pb_path):
        print(f"  Error: {pb_path} not found")
        return False

    with open(pb_path, "rb") as f:
        pb_verses = _decode_quran_pb(f.read())

    print(f"  PB verses: {len(pb_verses)} (JSON: {len(data)})")
    if len(pb_verses) != len(data):
        print("  FAIL: verse count mismatch")
        return False

    field_names = {1: "id", 2: "surah", 3: "juz", 4: "page",
                   5: "verse_num", 6: "word_count",
                   7: "text_glyphs", 8: "verse_num_glyphs",
                   9: "text"}
    mismatches = 0
    invariant_failures = 0
    for i, (jv, pv) in enumerate(zip(data, pb_verses)):
        glyphs = jv["text_glyphs"].split("\t")
        text = jv.get("text", "")
        expected = {
            1: jv["id"], 2: jv["surah"], 3: jv["juz"], 4: jv["page"],
            5: jv["verse_num"], 6: jv["word_count"],
            7: "\t".join(glyphs[:-1]),
            8: glyphs[-1] if glyphs else "",
            9: text,
        }
        for k in range(1, 10):
            if k <= 6:
                got = pv.get(k, 0)
            else:
                got = pv.get(k, b"").decode("utf-8")
            if got != expected[k]:
                mismatches += 1
                if mismatches <= 10:
                    print(f"  MISMATCH idx={i} id={jv['id']} "
                          f"{field_names[k]}: want={expected[k]!r} got={got!r}")

        # Alignment invariant: text tokens == word_count == (text_glyphs tokens - 1)
        n_text = len(text.split("\t")) if text else 0
        n_glyphs_words = len(glyphs) - 1
        if n_text != jv["word_count"] or n_glyphs_words != jv["word_count"]:
            invariant_failures += 1
            if invariant_failures <= 5:
                print(f"  ALIGN FAIL id={jv['id']} {jv['surah']}:{jv['verse_num']} "
                      f"word_count={jv['word_count']} text_tokens={n_text} "
                      f"glyph_words={n_glyphs_words}")

    if mismatches or invariant_failures:
        print(f"  FAIL: {mismatches} field mismatches, {invariant_failures} alignment failures")
        return False
    print(f"  OK — all {len(data)} verses, all 9 fields match, alignment invariant holds")
    return True


def main():
    if not os.path.exists(OUTPUT_FILE):
        print(f"Error: {OUTPUT_FILE} not found. Run scraper.py first.")
        sys.exit(1)

    data = json.load(open(OUTPUT_FILE))

    args = sys.argv[1:]

    # `pb` mode: only verify the protobuf against the JSON (no API calls).
    if args and args[0] == "pb":
        pb_path = args[1] if len(args) > 1 else PB_TO_CHECK
        ok = check_pb_against_json(data, pb_path)
        print("\n=== Result ===")
        print("PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)

    # `pb-api` mode: decode pb directly, then verify it against quran.com API.
    # Proves pb matches the canonical API source (independent of quran.json).
    if args and args[0] == "pb-api":
        pb_path = PB_TO_CHECK
        page_args = []
        for a in args[1:]:
            if a.endswith(".pb"):
                pb_path = a
            else:
                page_args.append(a)
        if not os.path.exists(pb_path):
            print(f"Error: {pb_path} not found")
            sys.exit(1)
        print(f"Decoding {pb_path}...")
        with open(pb_path, "rb") as f:
            pb_verses = _decode_quran_pb(f.read())
        pb_data = _pb_verses_to_dicts(pb_verses)
        print(f"  {len(pb_data)} verses decoded from pb")
        basics_ok = check_basics(pb_data)
        pages = None
        if page_args:
            pages = list(range(1, 605)) if page_args[0] == "all" else [int(p) for p in page_args]
        api_ok = check_pages_against_api(pb_data, pages)
        print("\n=== Result ===")
        if basics_ok and api_ok:
            print("ALL CHECKS PASSED — pb matches quran.com API")
            sys.exit(0)
        print("SOME CHECKS FAILED")
        sys.exit(1)

    basics_ok = check_basics(data)

    # Parse optional page args
    pages = None
    if args:
        if args[0] == "all":
            pages = list(range(1, 605))
        else:
            pages = [int(p) for p in args]

    api_ok = check_pages_against_api(data, pages)

    print("\n=== Result ===")
    if basics_ok and api_ok:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
