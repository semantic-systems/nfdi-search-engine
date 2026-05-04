from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from nfdi_search_engine.services.deduplication.normalize import normalize_name, normalize_orcid


@dataclass(frozen=True)
class ResearcherPolicy:
    """
    Deduplicate researchers by ORCID (primary) and name(s) (secondary).

    Primary pass: researchers sharing the same ORCID are always merged.
    Secondary pass: researchers sharing a name (or alternate name) are clustered,
    then merged only if exactly one member has an ORCID. That entry becomes the anchor.
    Clusters with no ORCID (no reliable anchor) or multiple ORCIDs (different people)
    are left unmerged.
    """

    category: str = "researchers"

    def primary_keys(self, obj: Any) -> Iterable[str]:
        """Returns a normalized ORCID prefixed with 'orcid:' if available, else an empty iterable"""
        key = normalize_orcid(getattr(obj, "identifier", ""))
        if key:
            yield f"orcid:{key}"

    def secondary_keys(self, obj: Any) -> Iterable[str]:
        """Returns normalized name variants prefixed with 'name:' """
        names = set()
        if name := normalize_name(getattr(obj, "name", "")):
            names.add(name)
        for alt in (getattr(obj, "alternateName", None) or []):
            if n := normalize_name(alt):
                names.add(n)
        for name in names:
            yield f"name:{name}"

    def should_merge_secondary_group(self, group: list[Any]) -> bool:
        """
        Returns True if only one object in the group has a valid ORCID (ideal anchor),
        False if ambiguous (no ORCID or multiple ORCIDs)
        """
        orcids = {normalize_orcid(getattr(r, "identifier", "")) for r in group}
        orcids.discard("")
        return len(orcids) == 1
