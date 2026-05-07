from typing import Any, Iterable, Protocol


class DedupPolicy(Protocol):
    """Interface for a category-specific deduplication strategy.

    A policy defines how to identify and cluster duplicate objects within one result category.
    The DeduplicationService runs two passes per policy:
    - primary pass: cluster by primary_keys and merge each cluster unconditionally
    - secondary pass: cluster by secondary_keys and merge clusters that pass should_merge_secondary_group

    To add dedup for a new category, implement this protocol and register an instance in policies/__init__.py.
    """

    # the category this policy applies to (e.g. "publications", "researchers")
    category: str

    def primary_keys(self, obj: Any) -> Iterable[str]:
        """
        Objects sharing a primary key are always merged.

        Examples: DOI for publications or ORCID for researchers.
        Should yield at most one key per object in practice.
        """
        ...

    def secondary_keys(self, obj: Any) -> Iterable[str]:
        """
        Objects with a shared secondary key are candidates for merging,
        but are only merged if should_merge_secondary_group approves.
        Use this for more fuzzy matching, e.g. based on name similarity.

        Examples: name variants for researchers.
        Return an empty iterable to skip the secondary pass for this category.
        """
        ...

    def should_merge_secondary_group(self, group: list[Any]) -> bool:
        """
        Receives a list of objects that share a secondary key and
        returns True if they should be merged (else false).

        Called for every cluster of size > 1 found in the secondary pass.
        Use this to add a safety condition before merging, e.g. require
        exactly one ORCID anchor in a name cluster to avoid merging different people.
        """
        ...
