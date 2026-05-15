from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from nfdi_search_engine.services.deduplication.merger import ObjectMerger
from nfdi_search_engine.services.deduplication.policies.base import DedupPolicy
from nfdi_search_engine.infra.observability.decorators import traced

log = logging.getLogger(__name__)


class DeduplicationService:
    """
    This service handles deduplication of search results across all categories, using category-specific policies.
    Pass a results dictionary to deduplicate(), and it will return a new dictionary with the same structure but
    duplicate objects merged according to the policies (see `nfdi_search_engine/services/deduplication/policies`).
    """

    def __init__(self, policies: list[DedupPolicy], mapping_preference: dict) -> None:
        self.policies = policies
        self.mapping_preference = mapping_preference
        self.merger = ObjectMerger()

    @traced(
        "deduplication_service.deduplicate",
        attrs=lambda self, results: {
            "policies.count": len(self.policies),
            "results.category_count": len(results)
        }
    )
    def deduplicate(self, results: dict) -> dict:
        """Deduplicate search results according to the policies."""
        for policy in self.policies:
            pref = self.mapping_preference.get(policy.category, {})
            objects = results.get(policy.category, [])
            objects = self._primary_pass(objects, policy, pref)
            objects = self._secondary_pass(objects, policy, pref)
            results[policy.category] = objects
        return results

    def _primary_pass(self, objects: list[Any], policy: DedupPolicy, pref: dict) -> list[Any]:
        """
        Cluster by primary keys and merge each cluster.

        Always runs merge even for groups of size 1 to clean up union-strategy list fields
        (e.g. deduplicate affiliations within a single source object).
        """
        keyed: dict[str, list[Any]] = {}    # objects with a primary key, grouped by key
        no_key: list[Any] = []              # objects without a primary key, to be merged individually at the end

        for obj in objects:
            key = next(iter(policy.primary_keys(obj)), None)
            if key:
                keyed.setdefault(key, []).append(obj)
            else:
                no_key.append(obj)

        # merge each primary-key cluster
        merged = []
        for group in keyed.values():
            try:
                merged.append(self.merger.merge(group, pref))
            except Exception as e:
                log.warning("merge failed for primary-key cluster (%s): %s", [getattr(o, "identifier", None) for o in group], e)
                merged.extend(group)

        # merge keyless objects individually (e.g. to clean up union fields)
        for obj in no_key:
            try:
                merged.append(self.merger.merge([obj], pref))
            except Exception as e:
                log.warning("merge failed for keyless object: %s", e)
                merged.append(obj)

        return merged

    def _secondary_pass(self, objects: list[Any], policy: DedupPolicy, pref: dict) -> list[Any]:
        """
        Cluster by secondary keys. Only merge clusters for which should_merge_secondary_group() returns True.

        Objects not qualifying for a merge (ambiguous clusters, singletons) are returned as-is.
        """
        n = len(objects)
        if n < 2:
            return objects

        # build key -> object index map
        key_sets = [list(policy.secondary_keys(obj)) for obj in objects]
        key_to_indices: dict[str, list[int]] = defaultdict(list)
        for i, keys in enumerate(key_sets):
            for key in keys:
                key_to_indices[key].append(i)

        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        # for each key, union all objects sharing this key into a cluster
        for indices in key_to_indices.values():
            for i in range(1, len(indices)):
                parent[find(indices[0])] = find(indices[i])

        groups: dict[int, list[int]] = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)

        result = []
        for group_indices in groups.values():
            group = [objects[i] for i in group_indices]

            if len(group_indices) == 1:
                result.append(group[0])
                continue

            # should we merge this cluster?
            if policy.should_merge_secondary_group(group):
                # merge it
                try:
                    result.append(self.merger.merge(group, pref))
                except Exception as e:
                    log.warning("merge failed for secondary-key cluster: %s", e)
                    result.extend(group)
            else:
                # don't merge, there is some ambiguity
                result.extend(group)

        return result
