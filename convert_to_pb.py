#!/usr/bin/env python3
"""
Converts quran.json to quran.pb (protobuf) matching the Kotlin DecodedQuran schema.

DecodedVerse fields (kotlinx.serialization.protobuf field order):
  1: id (int32)
  2: surah (int32)
  3: juz (int32)
  4: page (int32)
  5: verse_num (int32)
  6: word_count (int32)
  7: text_glyphs (string) - word glyphs concatenated, each char = one glyph
  8: verse_num_glyphs (string) - end marker glyph

DecodedQuran:
  1: verses (repeated DecodedVerse)
"""

import json
import os
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Protobuf wire format helpers ──

def encode_varint(value):
    """Encode an unsigned integer as a varint."""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def encode_tag(field_number, wire_type):
    """Encode a field tag (field_number << 3 | wire_type)."""
    return encode_varint((field_number << 3) | wire_type)


def encode_int_field(field_number, value):
    """Encode an int32 field (wire type 0 = varint)."""
    if value == 0:
        return b""  # default value, omit
    return encode_tag(field_number, 0) + encode_varint(value)


def encode_string_field(field_number, value):
    """Encode a string field (wire type 2 = length-delimited)."""
    if not value:
        return b""  # empty string, omit
    encoded = value.encode("utf-8")
    return encode_tag(field_number, 2) + encode_varint(len(encoded)) + encoded


def encode_bytes_field(field_number, value):
    """Encode a bytes/message field (wire type 2 = length-delimited)."""
    return encode_tag(field_number, 2) + encode_varint(len(value)) + value


def encode_verse(verse, text_glyphs, verse_num_glyphs):
    """Encode a single DecodedVerse message."""
    msg = bytearray()
    msg += encode_int_field(1, verse["id"])
    msg += encode_int_field(2, verse["surah"])
    msg += encode_int_field(3, verse["juz"])
    msg += encode_int_field(4, verse["page"])
    msg += encode_int_field(5, verse["verse_num"])
    msg += encode_int_field(6, verse["word_count"])
    msg += encode_string_field(7, text_glyphs)
    msg += encode_string_field(8, verse_num_glyphs)
    return bytes(msg)


def encode_quran(verses_data):
    """Encode the full DecodedQuran message."""
    msg = bytearray()
    for v in verses_data:
        glyphs = v["code"].split("\t")
        # All glyphs except last = word glyphs (tab-separated), last = end marker
        text_glyphs = "\t".join(glyphs[:-1])
        verse_num_glyphs = glyphs[-1] if glyphs else ""

        verse_bytes = encode_verse(v, text_glyphs, verse_num_glyphs)
        msg += encode_bytes_field(1, verse_bytes)
    return bytes(msg)


def main():
    json_path = os.path.join(BASE_DIR, "data", "quran.json")
    pb_path = os.path.join(BASE_DIR, "data", "quran.pb")

    print("Loading JSON...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Encoding {len(data)} verses to protobuf...")
    pb_bytes = encode_quran(data)

    with open(pb_path, "wb") as f:
        f.write(pb_bytes)

    print(f"Written {len(pb_bytes)} bytes to {pb_path}")

    # Verify sample
    v = data[0]
    glyphs = v["code"].split(" ")
    print(f"\nSample verse 1:")
    print(f"  text_glyphs: {repr(''.join(glyphs[:-1]))} ({len(''.join(glyphs[:-1]))} chars)")
    print(f"  verse_num_glyphs: {repr(glyphs[-1])}")
    print(f"  word_count: {v['word_count']}")


if __name__ == "__main__":
    main()
