"""Evidence flags only: never repairs or normalizes source strings."""

import re
import unicodedata
from collections import Counter
from functools import lru_cache

ESCAPE = re.compile(r"_x[0-9A-Fa-f]{4}_")
MOJIBAKE = re.compile(r"(?:[ÃÂ][\x80-\xbf]|á[º»])")


def _flags(text):
    result = []
    if "\0" in text:
        result.append("nul_character")
    if "_x" in text and ESCAPE.search(text):
        result.append("ooxml_escape_literal")
    if text.isascii():
        return tuple(result)
    if "\ufffd" in text:
        result.append("replacement_character")
    if any("\x80" <= c <= "\x9f" for c in text):
        result.append("c1_control")
    if not unicodedata.is_normalized("NFC", text):
        result.append("non_nfc")
    if MOJIBAKE.search(text):
        result.append("mojibake_suspect")
    return tuple(result)


cached_flags = lru_cache(maxsize=8192)(_flags)


class TextQuality:
    def __init__(self):
        self.counts, self.locations, self.scanned = Counter(), {}, 0

    def add(self, value, row, column):
        if value is None:
            return
        self.scanned += 1
        for flag in cached_flags(value) if len(value) <= 512 else _flags(value):
            self.counts[flag] += 1
            locations = self.locations.setdefault(flag, [])
            if len(locations) < 5:
                locations.append({"source_row": row, "column": column})

    def record(self):
        return {
            "scanned_strings": self.scanned,
            "flag_counts": dict(sorted(self.counts.items())),
            "coordinates": self.locations,
            "values_repaired": False,
            "legacy_font_detection": "deferred_no_verified_mapping",
            "meaning": "heuristic evidence requiring review, not proof of corruption",
        }
