"""Syntax-only JSON ID routing; no data access or pipeline imports."""

import json
import re

MAX_RECORD_BYTES = 4 * 1024 * 1024
NUM = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")


def project_id(raw: bytes) -> str:
    """Inspect JSON syntax, top-level keys and id only; other strings stay bytes."""
    n = len(raw)

    def ws(i):
        while i < n and raw[i] in b" \t\r\n":
            i += 1
        return i

    def string_end(i):
        if i >= n or raw[i] != 34:
            raise ValueError("Expected JSON string envelope")
        i += 1
        while i < n:
            c = raw[i]
            if c == 34:
                return i + 1
            if c < 32:
                raise ValueError("Control byte in JSON string")
            if c == 92:
                i += 1
                if i >= n or raw[i] not in b'"\\/bfnrtu':
                    raise ValueError("Invalid JSON escape")
                if raw[i] == 117:
                    if i + 4 >= n or any(
                        c not in b"0123456789abcdefABCDEF" for c in raw[i + 1 : i + 5]
                    ):
                        raise ValueError("Invalid JSON unicode escape")
                    i += 4
            i += 1
        raise ValueError("Unterminated JSON string")

    def skip(i, depth=0):
        i = ws(i)
        if depth > 32 or i >= n:
            raise ValueError("JSON routing depth/length limit")
        c = raw[i]
        if c == 34:
            return string_end(i)
        if c in (91, 123):
            close = 93 if c == 91 else 125
            j = ws(i + 1)
            if j < n and raw[j] == close:
                return j + 1
            while True:
                if c == 123:
                    j = ws(string_end(j))
                    if j >= n or raw[j] != 58:
                        raise ValueError("Invalid object envelope")
                    j = ws(j + 1)
                j = ws(skip(j, depth + 1))
                if j < n and raw[j] == close:
                    return j + 1
                if j >= n or raw[j] != 44:
                    raise ValueError("Invalid nested JSON envelope")
                j = ws(j + 1)
        for literal in (b"true", b"false", b"null"):
            if raw.startswith(literal, i):
                return i + len(literal)
        match = NUM.match(raw, i)
        if match:
            return match.end()
        raise ValueError("Invalid JSON value envelope")

    i = ws(0)
    if i >= n or raw[i] != 123:
        raise ValueError("JSONL requires an object envelope")
    i = ws(i + 1)
    identifier = None
    keys = set()
    while i < n and raw[i] != 125:
        end = string_end(i)
        try:
            key = json.loads(raw[i:end])
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Invalid top-level key encoding") from exc
        if key in keys:
            raise ValueError("Duplicate top-level JSON key")
        keys.add(key)
        i = ws(end)
        if i >= n or raw[i] != 58:
            raise ValueError("Missing key separator")
        i = ws(i + 1)
        end = skip(i)
        if key == "id":
            if raw[i] != 34:
                raise ValueError("ID must be a string token")
            try:
                identifier = json.loads(raw[i:end])
            except (ValueError, UnicodeError) as exc:
                raise ValueError("Invalid ID encoding") from exc
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError("Nonempty string ID required")
        i = ws(end)
        if i < n and raw[i] == 44:
            i = ws(i + 1)
            if i < n and raw[i] == 125:
                raise ValueError("Trailing comma")
        elif i >= n or raw[i] != 125:
            raise ValueError("Invalid record separator")
    if i >= n or raw[i] != 125 or ws(i + 1) != n or identifier is None:
        raise ValueError("Invalid JSON record termination or missing ID")
    return identifier
