from nfdi_search_engine.services.deduplication.policies.publications import PublicationPolicy
from nfdi_search_engine.services.deduplication.policies.researchers import ResearcherPolicy
from nfdi_search_engine.services.deduplication.policies.resources import ResourcePolicy
from nfdi_search_engine.services.deduplication.policies.base import DedupPolicy


def default_policies() -> list[DedupPolicy]:
    """
    Return the default set of active deduplication policies.

    To add dedup for a new category: implement DedupPolicy and register it here.
    """
    return [
        PublicationPolicy(),
        ResearcherPolicy(),
        ResourcePolicy(),
    ]
