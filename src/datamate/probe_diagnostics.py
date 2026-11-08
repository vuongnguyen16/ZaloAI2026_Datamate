"""Diagnostic sanitization usable by the stdlib-only outer cloud process."""

import re
from urllib.parse import urlsplit, urlunsplit


def sanitize_diagnostic(text: str) -> str:
    def without_query(match):
        parts = urlsplit(match.group())
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    text = re.sub(r"https?://[^\s)]+", without_query, text)
    # Redact authorization as one value before generic keys can remove the
    # word Bearer and leave its credential behind. Diagnostics are plain text.
    text = re.sub(r"(?im)(authorization\s*[:=]\s*)[^\r\n]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", text)
    text = re.sub(
        r"(?i)(token[_-]?secret|token|secret|authorization|password)(\s*[:=]\s*)[^\s,]+",
        r"\1\2[REDACTED]",
        text,
    )
    return re.sub(
        r"\b(?:ak-|as-|hf_|ghp_|github_pat_)[A-Za-z0-9_-]+", "[REDACTED]", text
    )
