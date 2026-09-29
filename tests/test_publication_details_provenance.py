"""Legacy publication details provenance service tests."""

from nfdi_search_engine.common.models.objects import Article, thing
from nfdi_search_engine.services.deduplication.merger import ObjectMerger
from nfdi_search_engine.services.publication_details_service import PublicationDetailsService
from nfdi_search_engine.common.models.details_settings import DetailsSettings


PUBLICATION_PREF = {
    "publications": {
        "__default__": [
            "CROSSREF - Publications",
            "OPENALEX - Publications",
        ],
        "citationCount": "max",
        "keywords": "union",
    },
}


def _article(*, name: str, source_name: str, doi: str = "10.5555/merged") -> Article:
    return Article(
        name=name,
        identifier=doi,
        description=f"Abstract for {name}",
        keywords=["AI", "NLP"],
        source=[thing(name=source_name, identifier=doi, url=f"https://doi.org/{doi}")],
    )


class DummyTracking:
    def log_event_async(self, **kwargs):
        return None


def _details_service(merger: ObjectMerger) -> PublicationDetailsService:
    return PublicationDetailsService(
        settings=DetailsSettings(
            data_sources={},
            mapping_preference=PUBLICATION_PREF,
        ),
        tracking=DummyTracking(),
        merger=merger,
    )


class TestPublicationDetailsProvenance:
    def test_merge_publications_uses_injected_shared_merger(self):
        merger = ObjectMerger(enable_provenance=True)
        svc = _details_service(merger)
        assert svc.merger is merger

    def test_merge_publications_returns_empty_rows_when_disabled(self):
        svc = _details_service(ObjectMerger(enable_provenance=False))
        publication, rows = svc.merge_publications(
            [
                _article(name="Paper", source_name="CROSSREF - Publications"),
                _article(name="Paper", source_name="OPENALEX - Publications"),
            ]
        )
        assert isinstance(publication, Article)
        assert rows == []

    def test_merge_publications_handles_missing_publications(self):
        svc = _details_service(ObjectMerger(enable_provenance=True))
        publication, rows = svc.merge_publications([])
        assert publication is None
        assert rows == []
