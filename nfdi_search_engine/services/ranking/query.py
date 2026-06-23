from dataclasses import dataclass

from nfdi_search_engine.common.strings import tokenize


@dataclass
class Query:
    """
    Parsed representation of a user search query.

    Carries the normalized raw query string for phrase/exact matching and a token list for
    text-overlap scoring.
    """

    raw: str
    tokens: list[str]

    @classmethod
    def from_string(cls, query: str) -> "Query":
        return cls(raw=query.strip().lower(), tokens=tokenize(query))
