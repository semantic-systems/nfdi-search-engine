from nfdi_search_engine.common.models.objects import Article, thing
from nfdi_search_engine.common.models.search_result import SearchResult
from nfdi_search_engine.services.deduplication.merger import ObjectMerger

PUBLICATION_PREF = {
    "__default__": [
        "CROSSREF - Publications",
        "OPENALEX - Publications",
    ],
    "citationCount": "max",
    "keywords": "union",
}


def _source(name: str) -> thing:
    return thing(name=name)


def _article(
    *,
    name: str = "",
    abstract: str = "",
    citation_count: str = "",
    keywords: list[str] | None = None,
    source_name: str = "",
) -> Article:
    article = Article(
        name=name,
        abstract=abstract,
        citationCount=citation_count,
        keywords=keywords or [],
        source=[_source(source_name)] if source_name else [],
    )
    return article


class TestObjectMergerFieldProvenance:
    def test_disabled_mode_matches_plain_merge(self):
        merger = ObjectMerger(enable_provenance=False)
        group = [
            _article(name="Paper A", abstract="From Crossref", source_name="CROSSREF - Publications"),
            _article(name="Paper A", abstract="From OpenAlex", source_name="OPENALEX - Publications"),
        ]

        result = merger.merge(group, PUBLICATION_PREF, category="publications")

        assert isinstance(result, SearchResult)
        assert result.item.name == "Paper A"
        assert result.item.abstract == "From Crossref"
        assert result.field_provenance == {}
        assert result.item_dict() == result.item.model_dump(mode="python", exclude_none=True)

    def test_multi_source_merge_wraps_fields_with_sources(self):
        merger = ObjectMerger(enable_provenance=True)
        group = [
            _article(
                name="Paper A",
                abstract="Crossref abstract",
                citation_count="10",
                keywords=["nlp"],
                source_name="CROSSREF - Publications",
            ),
            _article(
                name="Paper A",
                abstract="OpenAlex abstract",
                citation_count="25",
                keywords=["semantics"],
                source_name="OPENALEX - Publications",
            ),
        ]

        result = merger.merge(group, PUBLICATION_PREF, category="publications")
        payload = result.item_dict()

        assert payload["name"] == {
            "value": "Paper A",
            "sources": ["CROSSREF - Publications", "OPENALEX - Publications"],
        }
        assert payload["abstract"] == {
            "value": "Crossref abstract",
            "sources": ["CROSSREF - Publications", "OPENALEX - Publications"],
        }
        assert payload["citationCount"] == {
            "value": "25",
            "sources": ["CROSSREF - Publications", "OPENALEX - Publications"],
        }
        assert payload["keywords"] == {
            "value": ["nlp", "semantics"],
            "sources": ["CROSSREF - Publications", "OPENALEX - Publications"],
        }
        assert result.item.name == "Paper A"
        assert result.item.citationCount == "25"

    def test_single_source_merge_still_emits_source_list(self):
        merger = ObjectMerger(enable_provenance=True)
        article = _article(
            name="Solo Paper",
            abstract="Only one source",
            source_name="OPENALEX - Publications",
        )

        result = merger.merge([article], PUBLICATION_PREF, category="publications")
        payload = result.item_dict()

        assert payload["name"] == {
            "value": "Solo Paper",
            "sources": ["OPENALEX - Publications"],
        }
        assert payload["abstract"] == {
            "value": "Only one source",
            "sources": ["OPENALEX - Publications"],
        }

    def test_missing_source_metadata_uses_empty_sources(self):
        merger = ObjectMerger(enable_provenance=True)
        article = Article(name="No Source Metadata", abstract="Plain object")

        result = merger.merge([article], PUBLICATION_PREF, category="publications")
        payload = result.item_dict()

        assert payload["name"]["value"] == "No Source Metadata"
        assert payload["name"]["sources"] == []
        assert payload["abstract"]["value"] == "Plain object"
        assert payload["abstract"]["sources"] == []

    def test_merge_without_category_returns_plain_domain_object(self):
        merger = ObjectMerger(enable_provenance=True)
        group = [
            _article(name="Paper A", source_name="CROSSREF - Publications"),
            _article(name="Paper A", source_name="OPENALEX - Publications"),
        ]

        merged = merger.merge(group, PUBLICATION_PREF)

        assert isinstance(merged, Article)
        assert not isinstance(merged, SearchResult)
        assert merged.name == "Paper A"

    def test_per_merge_flag_overrides_constructor_default(self):
        merger = ObjectMerger(enable_provenance=False)
        article = _article(name="Flag Test", source_name="OPENALEX - Publications")

        result = merger.merge(
            [article],
            PUBLICATION_PREF,
            category="publications",
            enable_provenance=True,
        )

        assert result.field_provenance
        assert result.item_dict()["name"]["sources"] == ["OPENALEX - Publications"]
