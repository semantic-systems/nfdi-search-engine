"""Integration tests for field-level provenance through dedup and search."""

from nfdi_search_engine.common.models.objects import Article, thing
from nfdi_search_engine.common.models.search_result import SearchResult
from nfdi_search_engine.common.models.search_settings import SearchSettings
from nfdi_search_engine.services.deduplication.merger import ObjectMerger
from nfdi_search_engine.services.deduplication.policies import default_policies
from nfdi_search_engine.services.deduplication.service import DeduplicationService
from nfdi_search_engine.services.search_service import SearchService


PUBLICATION_PREF = {
    "publications": {
        "__default__": [
            "CROSSREF - Publications",
            "OPENALEX - Publications",
            "OPENAIRE - Products",
        ],
        "citationCount": "max",
        "keywords": "union",
    },
}


def _source(name: str, doi: str = "10.5555/x") -> thing:
    return thing(name=name, identifier=doi, url=f"https://doi.org/{doi}")


def _article(
    *,
    name: str,
    source_name: str,
    doi: str = "10.5555/merged",
    description: str = "Test abstract",
) -> Article:
    return Article(
        name=name,
        identifier=doi,
        description=description,
        source=[_source(source_name, doi)],
    )


class DummyService:
    pass


def _search_service(enable_provenance: bool) -> SearchService:
    dedup = DeduplicationService(
        default_policies(),
        PUBLICATION_PREF,
        enable_provenance=enable_provenance,
    )
    settings = SearchSettings(data_sources={}, enable_provenance=enable_provenance)
    return SearchService(
        settings,
        DummyService(),
        DummyService(),
        DummyService(),
        dedup,
        DummyService(),
    )


class TestProvenanceIntegration:
    def test_config_flag_enables_merger_and_search_service(self):
        svc = _search_service(enable_provenance=True)
        assert svc.deduplication.merger.enable_provenance is True
        assert svc.settings.enable_provenance is True

    def test_deduplication_populates_field_provenance_for_merged_publications(self):
        dedup = DeduplicationService(
            default_policies(),
            PUBLICATION_PREF,
            enable_provenance=True,
        )
        raw = {
            "publications": [
                _article(
                    name="Shared Title",
                    source_name="CROSSREF - Publications",
                ),
                _article(
                    name="Shared Title",
                    source_name="OPENALEX - Publications",
                ),
            ],
            "researchers": [],
            "resources": [],
            "organizations": [],
            "events": [],
            "projects": [],
            "others": [],
        }

        results = dedup.deduplicate(raw)
        assert len(results["publications"]) == 1

        merged = results["publications"][0]
        assert isinstance(merged, SearchResult)
        assert merged.field_provenance["name"].value == "Shared Title"
        assert merged.field_provenance["name"].sources == [
            "CROSSREF - Publications",
            "OPENALEX - Publications",
        ]

    def test_search_service_items_returns_plain_domain_objects(self):
        svc = _search_service(enable_provenance=True)
        result = ObjectMerger(enable_provenance=True).merge(
            [
                _article(name="Paper", source_name="OPENALEX - Publications"),
            ],
            PUBLICATION_PREF["publications"],
            category="publications",
        )

        items = svc._items([result])
        assert items[0].__class__.__name__ == "Article"

    def test_item_dict_serializes_field_provenance(self):
        dedup = DeduplicationService(
            default_policies(),
            PUBLICATION_PREF,
            enable_provenance=True,
        )
        raw = {
            "publications": [
                _article(name="Paper", source_name="CROSSREF - Publications", doi="10.5555/a"),
                _article(name="Paper", source_name="OPENALEX - Publications", doi="10.5555/a"),
            ],
            "researchers": [],
            "resources": [],
            "organizations": [],
            "events": [],
            "projects": [],
            "others": [],
        }
        merged = dedup.deduplicate(raw)["publications"][0]

        assert merged.item_dict()["name"] == {
            "value": "Paper",
            "sources": ["CROSSREF - Publications", "OPENALEX - Publications"],
        }
