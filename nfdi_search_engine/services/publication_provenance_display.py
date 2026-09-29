"""Publication details page provenance presentation (display layer only)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from nfdi_search_engine.common.models.search_result import (
    ProvenanceDisplayRow,
    SearchResult,
)

# Ordered display configuration: internal field name -> user-facing label.
PUBLICATION_PROVENANCE_FIELDS: tuple[tuple[str, str], ...] = (
    ("name", "Title"),
    ("author", "Authors"),
    ("abstract", "Abstract"),
    ("keywords", "Keywords"),
    ("identifier", "DOI"),
    ("datePublished", "Publication date"),
    ("publication", "Publisher"),
    ("license", "License"),
    ("referenceCount", "References"),
    ("citationCount", "Citations"),
)

PUBLICATION_PROVENANCE_HIDDEN_FIELDS = frozenset(
    {
        "additionalType",
        "description",
        "originalSource",
        "partiallyLoaded",
        "rankScore",
        "source",
        "url",
    }
)

_LICENSE_LABEL_PATTERNS = (
    re.compile(
        r"Creative Commons\s+CC0\s+[\d.]+\s+Universal",
        re.IGNORECASE,
    ),
    re.compile(
        r"CC\s*BY(?:\s*[-\s]?\s*NC|\s*[-\s]?\s*SA|\s*[-\s]?\s*ND)*\s*[\d.]+",
        re.IGNORECASE,
    ),
    re.compile(r"CC0\s*[\d.]+", re.IGNORECASE),
)


def _truncate(text: str, max_len: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_authors(value: Any, *, max_len: int, max_names: int = 3) -> str:
    if not isinstance(value, list) or not value:
        return ""

    names: list[str] = []
    for author in value:
        name = getattr(author, "name", None) or ""
        name = str(name).strip()
        if name:
            names.append(name)

    if names:
        preview = ", ".join(names[:max_names])
        if len(names) > max_names:
            preview = f"{preview}, …"
        return _truncate(preview, max_len)

    return f"{len(value)} authors"


def _format_publication_date(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return ""

    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return f"{parsed.day} {parsed.strftime('%b %Y')}"
    except ValueError:
        pass

    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
            return f"{parsed.day} {parsed.strftime('%b %Y')}"
        except ValueError:
            pass

    return text


def _format_count(value: Any, unit: str) -> str:
    text = str(value).strip()
    if not text:
        return ""

    try:
        count = int(float(text))
    except (TypeError, ValueError):
        lowered = text.lower()
        if lowered.endswith(unit):
            return text
        return text

    return f"{count} {unit}"


def _extract_license_label(text: str) -> str | None:
    for pattern in _LICENSE_LABEL_PATTERNS:
        match = pattern.search(text)
        if match:
            return " ".join(match.group(0).split())
    return None


def _format_license_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if "creativecommons.org" not in parsed.netloc or not segments:
        return None

    if len(segments) >= 3 and segments[0] == "publicdomain" and segments[1] == "zero":
        return f"Creative Commons CC0 {segments[2]} Universal"

    if len(segments) >= 3 and segments[0] == "licenses":
        license_type = segments[1].upper().replace("-", " ")
        version = segments[2]
        if license_type == "BY":
            return f"CC BY {version}"
        return f"CC {license_type} {version}".strip()

    if len(segments) >= 2:
        return " ".join(segments[-2:]).replace("-", " ").title()

    return None


def _format_license(value: Any, *, max_len: int) -> str:
    text = str(value).strip()
    if not text:
        return ""

    label: str | None = None
    if text.startswith(("http://", "https://")):
        label = _format_license_from_url(text)
    else:
        label = _extract_license_label(text)

    if label:
        return _truncate(label, max_len)

    return _truncate(text, max_len)


def _format_default(value: Any, *, max_len: int) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return ""

    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return _truncate(", ".join(value), max_len)
        return ""

    if isinstance(value, dict):
        return _truncate(
            ", ".join(f"{key}: {val}" for key, val in list(value.items())[:3]),
            max_len,
        )

    return _truncate(getattr(value, "name", None) or str(value), max_len)


def _format_publication_provenance_value(
    field_name: str,
    value: Any,
    max_len: int,
) -> str:
    if field_name == "author":
        return _format_authors(value, max_len=max_len)
    if field_name == "datePublished":
        return _format_publication_date(value)
    if field_name == "referenceCount":
        return _format_count(value, "references")
    if field_name == "citationCount":
        return _format_count(value, "citations")
    if field_name == "license":
        return _format_license(value, max_len=max_len)
    return _format_default(value, max_len=max_len)


def publication_provenance_display_rows(
    result: SearchResult,
    *,
    max_value_len: int = 120,
) -> list[ProvenanceDisplayRow]:
    """
    Build curated provenance rows for the publication details modal.

    Reads only from SearchResult.field_provenance; does not generate provenance.
    """
    rows: list[ProvenanceDisplayRow] = []

    for field_name, label in PUBLICATION_PROVENANCE_FIELDS:
        if field_name in PUBLICATION_PROVENANCE_HIDDEN_FIELDS:
            continue

        fp = result.field_provenance.get(field_name)
        if fp is None or not fp.sources:
            continue

        value = _format_publication_provenance_value(
            field_name,
            fp.value,
            max_value_len,
        )
        if not value:
            continue

        rows.append(
            ProvenanceDisplayRow(
                field=label,
                value=value,
                sources=", ".join(fp.sources),
            )
        )

    return rows
