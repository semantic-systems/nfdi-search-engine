from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List

from nfdi_search_engine.common.merge import merge_objects

log = logging.getLogger(__name__)


def _normalize_identifier(raw: Any) -> str:
    """Normalize an identifier for comparison over multiple sources
    
    Examples:
    - "https://doi.org/10.1234/abc" -> "10.1234/abc"
    - "doi:10.1234/abc" -> "10.1234/abc"
    """
    if not raw:
        return ""
    s = str(raw).strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi: ", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    for prefix in ("https://orcid.org/", "http://orcid.org/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break

    # merge versioned identifiers like "10.1234/abc.v1" and "10.1234/abc.v2" into "10.1234/abc"
    # this regex removes suffixes like ".v1", ".v2", etc.
    version_suffix = re.compile(r"\.v\d+$")
    s = version_suffix.sub("", s)

    return s


def _normalize_name(name: str) -> str:
    """Normalize a researcher name for comparison over multiple sources"""
    if not name:
        return ""
    s = name.strip().lower()

    # remove titles like "Dr.", "Prof.", "Ing."
    re_title = re.compile(r"^(prof\.?\s+|dr\.?\s+|mr\.?\s+|mrs\.?\s+|ms\.?\s+|ing\.?\s+)+", re.IGNORECASE)
    s = re_title.sub("", s)
    s = s.replace(",", "")

    return " ".join(s.split())


def _name_set(researcher: Any) -> set:
    """All normalized names (name + alternateNames) for a researcher."""
    names = set()
    if primary := getattr(researcher, "name", ""):
        names.add(_normalize_name(primary))
    for alt in (getattr(researcher, "alternateName", None) or []):
        if alt:
            names.add(_normalize_name(alt))
    return names - {""}


def deduplicate_by_identifier(objects: List[Any], mapping_preference: dict) -> List[Any]:
    """Cluster objects by normalized identifier and merge each cluster"""
    keyed: Dict[str, List[Any]] = {}
    no_id: List[Any] = []

    for obj in objects:
        key = _normalize_identifier(getattr(obj, "identifier", ""))
        if key:
            keyed.setdefault(key, []).append(obj)
        else:
            no_id.append(obj)

    # always call merge_objects for single-element groups so that union
    # list fields (e.g. affiliation) are deduplicated within a single source object
    merged = []
    for group in keyed.values():
        try:
            merged.append(merge_objects(group, mapping_preference))
        except Exception as e:
            log.warning("merge_objects failed for identifier group (%s), keeping originals: %s", [getattr(o, "identifier", None) for o in group], e)
            merged.extend(group)

    cleaned_no_id = []
    for obj in no_id:
        try:
            cleaned_no_id.append(merge_objects([obj], mapping_preference))
        except Exception as e:
            log.warning("merge_objects failed for no-id object, keeping original: %s", e)
            cleaned_no_id.append(obj)

    return merged + cleaned_no_id


def deduplicate_researchers_by_name(researchers: List[Any], mapping_preference: dict) -> List[Any]:
    """
    Second dedup pass for researchers: merge entries that refer to the same person
    but couldn't be matched by ORCID (e.g. one source doesn't provide one).

    Researchers are clustered by shared names, including alternate names. A cluster
    is merged if exactly one member has an ORCID: that entry becomes the anchor and
    the others are merged into it. Clusters with no ORCID (no reliable anchor) or
    multiple ORCIDs (different people sharing a name alias) are left unmerged (ambiguous).
    """
    n = len(researchers)

    # if we only have one or zero researchers, no need to deduplicate
    if n < 2:
        return researchers

    # get all possible normalized names for each researcher, and build a map from name to researcher indices
    name_sets = [_name_set(r) for r in researchers]
    name_to_indices: Dict[str, List[int]] = defaultdict(list)
    for i, ns in enumerate(name_sets):
        for name in ns:
            name_to_indices[name].append(i)

    # each researcher starts in their own group
    # find() returns the group root
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # merge groups that share a name
    for indices in name_to_indices.values():
        for i in range(1, len(indices)):
            parent[find(indices[0])] = find(indices[i])

    # collect researchers by group
    groups: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    # for each cluster of researchers, if there's exactly one with an ORCID, merge the whole cluster
    # otherwise, keep them separate (but still clean list fields)
    result: List[Any] = []
    for group_indices in groups.values():
        group = [researchers[i] for i in group_indices]

        if len(group_indices) == 1:
            try:
                result.append(merge_objects(group, mapping_preference))
            except Exception as e:
                log.warning("merge_objects failed for single researcher, keeping original: %s", e)
                result.append(group[0])
            continue

        orcid_members = [r for r in group if _normalize_identifier(getattr(r, "identifier", ""))]

        if len(orcid_members) == 1:
            try:
                result.append(merge_objects(group, mapping_preference))
            except Exception as e:
                log.warning("merge_objects failed for researcher name-cluster, keeping originals: %s", e)
                result.extend(group)
        else:
            # dont merge if ambiguous (0 or 2+ ORCIDs), but still clean list fields within each researcher object
            for r in group:
                try:
                    result.append(merge_objects([r], mapping_preference))
                except Exception as e:
                    log.warning("merge_objects failed for ambiguous researcher, keeping original: %s", e)
                    result.append(r)

    return result


def deduplicate(
    results: Dict[str, List[Any]],
    categories: List[str],
    mapping_preference: dict,
) -> Dict[str, List[Any]]:
    
    # for each category, cluster by identifier and merge clusters
    for cat in categories:
        pref = mapping_preference.get(cat, {})
        results[cat] = deduplicate_by_identifier(results[cat], pref)

    # for researchers, also cluster by name (and alternative name) and merge clusters with one ORCID anchor
    if "researchers" in categories:
        pref = mapping_preference.get("researchers", {})
        results["researchers"] = deduplicate_researchers_by_name(results["researchers"], pref)

    return results
