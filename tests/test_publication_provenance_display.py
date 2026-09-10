"""Tests for publication provenance display configuration and formatting."""

from nfdi_search_engine.common.models.objects import Article, Author, thing
from nfdi_search_engine.common.models.search_result import (
    FieldValueProvenance,
    SearchResult,
)
from nfdi_search_engine.services.deduplication.merger import ObjectMerger
from nfdi_search_engine.services.publication_provenance_display import (
    publication_provenance_display_rows,
)


PUBLICATION_PREF = {
    "__default__": ["CROSSREF - Publications", "OPENALEX - Publications"],
    "citationCount": "max",
    "referenceCount": "max",
    "keywords": "union",
}


def _search_result(field_provenance: dict[str, FieldValueProvenance]) -> SearchResult:
    return SearchResult(
        category="publications",
        entity_key="publications:test",
        item=Article(name="Example"),
        field_provenance=field_provenance,
    )


class TestPublicationProvenanceDisplay:
    def test_rows_follow_configured_order_and_labels(self):
        result = _search_result(
            {
                "keywords": FieldValueProvenance(
                    value=["AI", "NLP"],
                    sources=["OPENALEX - Publications"],
                ),
                "name": FieldValueProvenance(
                    value="Example Paper",
                    sources=["CROSSREF - Publications"],
                ),
                "rankScore": FieldValueProvenance(
                    value=1.5,
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)

        assert [row.field for row in rows] == ["Title", "Keywords"]
        assert rows[0].value == "Example Paper"
        assert rows[1].value == "AI, NLP"

    def test_hidden_internal_fields_are_not_shown(self):
        result = _search_result(
            {
                "description": FieldValueProvenance(
                    value="Duplicate abstract",
                    sources=["OPENALEX - Publications"],
                ),
                "originalSource": FieldValueProvenance(
                    value="Crossref",
                    sources=["CROSSREF - Publications"],
                ),
                "source": FieldValueProvenance(
                    value=[thing(name="OPENALEX - Publications")],
                    sources=["OPENALEX - Publications"],
                ),
                "url": FieldValueProvenance(
                    value="https://example.org/paper",
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        assert publication_provenance_display_rows(result) == []

    def test_authors_show_names_when_available(self):
        result = _search_result(
            {
                "author": FieldValueProvenance(
                    value=[
                        Author(name="Ada Lovelace"),
                        Author(name="Grace Hopper"),
                        Author(name="Alan Turing"),
                        Author(name="Extra Author"),
                    ],
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)
        assert rows[0].field == "Authors"
        assert rows[0].value == "Ada Lovelace, Grace Hopper, Alan Turing, …"

    def test_authors_fallback_to_count_without_names(self):
        result = _search_result(
            {
                "author": FieldValueProvenance(
                    value=[Author(name=""), Author(name="")],
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)
        assert rows[0].value == "2 authors"

    def test_publication_date_is_human_friendly(self):
        result = _search_result(
            {
                "datePublished": FieldValueProvenance(
                    value="2020-08-01T04:18:32Z",
                    sources=["CROSSREF - Publications"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)
        assert rows[0].field == "Publication date"
        assert rows[0].value == "1 Aug 2020"

    def test_reference_and_citation_counts_include_units(self):
        result = _search_result(
            {
                "referenceCount": FieldValueProvenance(
                    value="42",
                    sources=["CROSSREF - Publications"],
                ),
                "citationCount": FieldValueProvenance(
                    value="25",
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        rows = {row.field: row.value for row in publication_provenance_display_rows(result)}
        assert rows["References"] == "42 references"
        assert rows["Citations"] == "25 citations"

    def test_license_prefers_readable_label_for_urls(self):
        result = _search_result(
            {
                "license": FieldValueProvenance(
                    value="https://creativecommons.org/licenses/by/4.0/",
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)
        assert rows[0].value == "CC BY 4.0"

    def test_license_extracts_short_label_from_long_descriptive_text(self):
        long_text = (
            "Alle im GESIS DBK veröffentlichten Metadaten sind frei verfügbar unter der "
            "Creative Commons CC0 1.0 Universal Public Domain Dedication. GESIS bittet "
            "jedoch darum, die Nutzung der Metadaten in Publikationen zu dokumentieren."
        )
        result = _search_result(
            {
                "license": FieldValueProvenance(
                    value=long_text,
                    sources=["GESIS KG"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)
        assert rows[0].value == "Creative Commons CC0 1.0 Universal"

    def test_license_truncates_unrecognized_long_text(self):
        long_text = "x" * 200
        result = _search_result(
            {
                "license": FieldValueProvenance(
                    value=long_text,
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)
        assert len(rows[0].value) == 120
        assert rows[0].value.endswith("...")

    def test_abstract_is_truncated(self):
        result = _search_result(
            {
                "abstract": FieldValueProvenance(
                    value="word " * 80,
                    sources=["OPENALEX - Publications"],
                ),
            }
        )

        rows = publication_provenance_display_rows(result)
        assert rows[0].field == "Abstract"
        assert len(rows[0].value) == 120
        assert rows[0].value.endswith("...")

    def test_config_covers_expected_publication_fields(self):
        from nfdi_search_engine.services.publication_provenance_display import (
            PUBLICATION_PROVENANCE_FIELDS,
        )

        configured_fields = [field_name for field_name, _ in PUBLICATION_PROVENANCE_FIELDS]
        assert configured_fields == [
            "name",
            "author",
            "abstract",
            "keywords",
            "identifier",
            "datePublished",
            "publication",
            "license",
            "referenceCount",
            "citationCount",
        ]


class TestPublicationDetailsProvenanceIntegration:
    def test_merge_publications_uses_display_rows(self):
        from nfdi_search_engine.services.publication_details_service import (
            PublicationDetailsService,
        )
        from nfdi_search_engine.common.models.details_settings import DetailsSettings

        class DummyTracking:
            def log_event_async(self, **kwargs):
                return None

        merger = ObjectMerger(enable_provenance=True)
        svc = PublicationDetailsService(
            settings=DetailsSettings(
                data_sources={},
                mapping_preference={"publications": PUBLICATION_PREF},
            ),
            tracking=DummyTracking(),
            merger=merger,
        )

        article = Article(
            name="Paper",
            identifier="10.5555/x",
            abstract="An abstract",
            source=[thing(name="OPENALEX - Publications")],
        )
        publication, rows = svc.merge_publications([article])

        assert publication.name == "Paper"
        assert rows
        assert rows[0].field == "Title"
