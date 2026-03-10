from __future__ import annotations

from urllib.parse import unquote


def parse_prefixed_param(raw: str) -> str:
    return raw.split(":", 1)[1] if ":" in raw else raw


def parse_prefixed_and_unquote(raw: str) -> str:
    return unquote(parse_prefixed_param(raw))
