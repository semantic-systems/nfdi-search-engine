from nfdi_search_engine.common.models.objects import Article, Author, Person, thing
from nfdi_search_engine.services.deduplication.merger import ObjectMerger
from nfdi_search_engine.web.details.provenance import provenance_rows

PUBLICATIONS = {
    "__default__": ["CROSSREF - Publications", "OPENALEX - Publications", "OPENAIRE - Products"],
    "citationCount": "max",
    "keywords": "union",
}

RESEARCHERS = {
    "__default__": ["OPENALEX - Researchers", "ORCID"],
    "works_count": "max",
}


def _article(source: str, **fields) -> Article:
    return Article(source=[thing(name=source)], **fields)


def _author(source: str, **fields) -> Author:
    return Author(source=[thing(name=source)], **fields)


def _rows(category: str, preference: dict, *items) -> dict:
    result = ObjectMerger().merge(list(items), preference, category=category)
    return {row.label: row for row in provenance_rows(result)}


def test_trivial_differences_share_a_group():
    rows = _rows(
        "publications",
        PUBLICATIONS,
        _article("OPENALEX - Publications", name="Deep  Learning."),
        _article("CROSSREF - Publications", name="deep learning"),
    )
    title = rows["Title"]
    assert title.value == "deep learning"
    assert [s.source for s in title.sources] == ["CROSSREF - Publications", "OPENALEX - Publications"]
    assert not title.conflict


def test_disagreeing_sources_get_distinct_groups_with_selected_first():
    rows = _rows(
        "publications",
        PUBLICATIONS,
        _article("OPENAIRE - Products", author=[Person(name="B")], citationCount="3"),
        _article("OPENALEX - Publications", author=[Person(name="A")], citationCount="7.0"),
    )
    authors = rows["Authors"]
    assert authors.conflict
    assert [(s.source, s.value, s.group) for s in authors.sources] == [
        ("OPENALEX - Publications", "A", 0),
        ("OPENAIRE - Products", "B", 1),
    ]
    assert rows["Citations"].value == "7"
    assert rows["Citations"].sources[0].source == "OPENALEX - Publications"


def test_union_ignores_order_and_empty_fields_are_skipped():
    rows = _rows(
        "publications",
        PUBLICATIONS,
        _article("CROSSREF - Publications", keywords=["a", "b"]),
        _article("OPENALEX - Publications", keywords=["B", "a"]),
    )
    assert not rows["Keywords"].conflict
    assert "Abstract" not in rows


def test_non_selected_sources_follow_preference_order():
    rows = _rows(
        "publications",
        PUBLICATIONS,
        _article("OPENAIRE - Products", name="C", citationCount="9"),
        _article("OPENALEX - Publications", name="B", citationCount="1"),
        _article("CROSSREF - Publications", name="A", citationCount="1"),
    )
    assert [s.source for s in rows["Title"].sources] == [
        "CROSSREF - Publications",
        "OPENALEX - Publications",
        "OPENAIRE - Products",
    ]
    # the winner leads, the rest fall back to the default order
    assert [s.source for s in rows["Citations"].sources] == [
        "OPENAIRE - Products",
        "CROSSREF - Publications",
        "OPENALEX - Publications",
    ]


def test_duplicate_items_from_one_source_keep_their_own_values():
    rows = _rows(
        "publications",
        PUBLICATIONS,
        _article("OPENALEX - Publications", name="First"),
        _article("OPENALEX - Publications", name="Second"),
    )
    assert [(s.source, s.value) for s in rows["Title"].sources] == [
        ("OPENALEX - Publications", "First"),
        ("OPENALEX - Publications", "Second"),
    ]


def test_researcher_orcid_forms_and_counts_match():
    rows = _rows(
        "researchers",
        RESEARCHERS,
        _author("ORCID", identifier="0000-0002-1825-0097", works_count="12"),
        _author(
            "OPENALEX - Researchers",
            identifier="https://orcid.org/0000-0002-1825-0097",
            works_count="12.0",
        ),
    )
    assert not rows["ORCID"].conflict
    assert not rows["Publications"].conflict


def test_unknown_category_has_no_rows():
    result = ObjectMerger().merge(
        [_article("CROSSREF - Publications", name="A")], PUBLICATIONS, category="resources"
    )
    assert provenance_rows(result) == []
