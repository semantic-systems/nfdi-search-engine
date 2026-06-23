import re


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def flatten_string_value(value: str | list[str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    return str(value)
