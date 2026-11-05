"""Exact full-scan counts and bounded deterministic examples."""

import hashlib
import re
from collections import Counter
from decimal import Decimal, InvalidOperation

from datamate.ingest import IngestError

NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def preview(value, limit):
    if value is None:
        return {"value": None, "utf8_bytes": None, "truncated": False}
    encoded = value.encode("utf-8")
    result = {"value": value, "utf8_bytes": len(encoded), "truncated": False}
    if len(encoded) > limit:
        # Input is already decoded strictly; ignore only the sliced trailing code point.
        result.update(
            value=encoded[:limit].decode("utf-8", errors="ignore"),
            truncated=True,
            sha256=hashlib.sha256(encoded).hexdigest(),
        )
    return result


class Retention:
    def __init__(self, limit):
        self.limit, self.used = limit, 0

    def replace(self, before, after):
        size = (
            self.used
            - (len(before.encode("utf-8")) if before is not None else 0)
            + len(after.encode("utf-8"))
        )
        if size > self.limit:
            raise IngestError(
                "profile_memory_limit", "Retained extrema exceed the unit byte budget"
            )
        self.used = size


class ColumnStats:
    def __init__(self, index, options, retention):
        self.index, self.options, self.retention = index, options, retention
        self.present = self.null = self.empty = self.nonempty = 0
        self.types = Counter()
        self.minimum = self.maximum = None
        self.min_chars = self.max_chars = self.min_bytes = self.max_bytes = None
        self.samples, self.sample_keys = [], set()
        self.numeric_counts = Counter(
            {k: 0 for k in ("finite", "nonfinite", "invalid", "too_long")}
        )
        self.numeric_min = self.numeric_max = None
        self.numeric_min_text = self.numeric_max_text = None

    def add(self, value, typ, row, location):
        self.present += 1
        self.types[typ] += 1
        if value is None:
            self.null += 1
            return
        if value == "":
            self.empty += 1
            return
        self.nonempty += 1
        chars, encoded = len(value), value.encode("utf-8")
        size = len(encoded)
        self.min_chars = chars if self.min_chars is None else min(self.min_chars, chars)
        self.max_chars = chars if self.max_chars is None else max(self.max_chars, chars)
        self.min_bytes = size if self.min_bytes is None else min(self.min_bytes, size)
        self.max_bytes = size if self.max_bytes is None else max(self.max_bytes, size)
        if self.minimum is None or value < self.minimum:
            self.retention.replace(self.minimum, value)
            self.minimum = value
        if self.maximum is None or value > self.maximum:
            self.retention.replace(self.maximum, value)
            self.maximum = value
        if len(self.samples) < self.options.samples_per_column:
            key = (
                value
                if size <= self.options.value_bytes
                else hashlib.sha256(encoded).hexdigest()
            )
            key = (size > self.options.value_bytes, key)
            if key not in self.sample_keys:
                self.sample_keys.add(key)
                self.samples.append(
                    {
                        "source_row": row,
                        **location,
                        **preview(value, self.options.value_bytes),
                    }
                )
        if typ not in {"xlsx:n", "sqlite:i", "sqlite:r"}:
            return
        if len(value) > self.options.max_numeric_chars:
            self.numeric_counts["too_long"] += 1
            return
        try:
            number = Decimal(value)
        except InvalidOperation:
            self.numeric_counts["invalid"] += 1
            return
        if not number.is_finite():
            self.numeric_counts["nonfinite"] += 1
            return
        if not NUMBER.fullmatch(value):
            self.numeric_counts["invalid"] += 1
            return
        self.numeric_counts["finite"] += 1
        if self.numeric_min is None or number < self.numeric_min:
            self.numeric_min, self.numeric_min_text = number, value
        if self.numeric_max is None or number > self.numeric_max:
            self.numeric_max, self.numeric_max_text = number, value

    def finish(self, rows):
        missing = rows - self.present
        if missing < 0 or self.present != self.null + self.empty + self.nonempty:
            raise IngestError("profile_counts", "Inconsistent cell counts")
        counts = {
            "present": self.present,
            "missing": missing,
            "null": self.null,
            "empty": self.empty,
            "nonempty": self.nonempty,
        }
        return {
            "position": self.index,
            "sql_name": f"c{self.index:04d}",
            "sql_type": "VARCHAR",
            "counts": counts,
            "ratios": {k: v / rows if rows else None for k, v in counts.items()},
            "physical_types": dict(sorted(self.types.items())),
            "length_nonempty": {
                "min_chars": self.min_chars,
                "max_chars": self.max_chars,
                "min_utf8_bytes": self.min_bytes,
                "max_utf8_bytes": self.max_bytes,
            },
            "lexical_nonempty": {
                "order": "Unicode code point, no normalization",
                "min": preview(self.minimum, self.options.value_bytes)
                if self.minimum is not None
                else None,
                "max": preview(self.maximum, self.options.value_bytes)
                if self.maximum is not None
                else None,
            },
            "numeric_physical_nonempty": {
                "basis": "finite Decimal comparison of physical numeric source lexemes only",
                **dict(self.numeric_counts),
                "min_lexeme": self.numeric_min_text,
                "max_lexeme": self.numeric_max_text,
            },
            "samples": self.samples,
        }
