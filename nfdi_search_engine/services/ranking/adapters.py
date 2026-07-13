from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from nfdi_search_engine.common.models.objects import Article, Author, Project


@dataclass(frozen=True)
class RankingDocument:
    """
    Normalized document passed from ranking adapters to ranking scorers.

    RankingDocument separates the raw domain object from the fields and features used for
    scoring. Text fields are used by FieldWeightedTextScorer, numeric and boolean features
    are used by FeatureScorer.
    """

    id: str
    category: str
    raw: Any

    fields: dict[str, str | list[str]] = field(default_factory=dict)
    numeric_features: dict[str, float | None] = field(default_factory=dict)
    boolean_features: dict[str, bool] = field(default_factory=dict)


class RankingAdapter(Protocol):
    """
    Interface for converting domain objects into RankingDocument objects.

    A ranking adapter is category-specific and should only support objects that can be
    represented meaningfully for that category's ranking profile.
    """

    category: str

    def supports(self, obj: object) -> bool:
        """
        Return whether this adapter can convert the given domain object.
        """
        ...

    def to_document(self, obj: object) -> RankingDocument:
        """
        Convert a supported domain object into a RankingDocument.
        """
        ...


class ArticleRankingAdapter(RankingAdapter):
    """
    Ranking adapter for publication search results represented as Article objects.

    Extracts publication-specific text fields such as title, abstract, keywords and authors,
    plus feature signals such as citation count, reference count and publication year.
    """

    category = "publications"

    def supports(self, obj: object) -> bool:
        return isinstance(obj, Article)

    def to_document(self, obj: Article) -> RankingDocument:
        title = obj.headline or obj.name or obj.alternativeHeadline

        authors = _names(obj.author)
        publisher = _name(obj.publisher)
        source_names = _source_names(obj)

        return RankingDocument(
            id=obj.identifier or obj.url or hash_fallback(obj),
            category=self.category,
            raw=obj,
            fields={
                "identifier": obj.identifier,
                "title": title,
                "aliases": obj.alternateName,
                "abstract": obj.abstract or obj.description,
                "body": obj.text or obj.articleBody,
                "keywords": obj.keywords,
                "authors": authors,
                "source": source_names or obj.originalSource,
                "publication": obj.publication,
                "publisher": publisher,
                "language": obj.inLanguage,
                "license": obj.license,
                "type": obj.additionalType,
                "genre": obj.genre,
                "version": obj.version,
            },
            numeric_features={
                "citation_count": safe_float(obj.citationCount),
                "reference_count": safe_float(obj.referenceCount),
                "year": safe_year(obj.datePublished or obj.dateCreated or obj.dateModified),
            },
            boolean_features={
                "has_identifier": bool(obj.identifier),
                "has_abstract": bool(obj.abstract or obj.description),
                "has_full_text": bool(obj.text or obj.articleBody),
                "has_open_access_url": bool(obj.encoding_contentUrl),
            },
        )


class AuthorRankingAdapter:
    """
    Ranking adapter for researcher search results represented as Author objects.

    Extracts name variants, affiliation/research-area text, optional generated profile text,
    works metadata, and researcher metrics such as works count and citation count.
    """

    category = "researchers"

    def supports(self, obj: object) -> bool:
        return isinstance(obj, Author)

    def to_document(self, obj: Author) -> RankingDocument:
        affiliations = _names(obj.affiliation)
        alumni = _names(obj.alumniOf)
        works = _titles(obj.works)
        works_for = _name(obj.worksFor)

        return RankingDocument(
            id=obj.identifier or obj.url or hash_fallback(obj),
            category=self.category,
            raw=obj,
            fields={
                "identifier": obj.identifier,
                "name": obj.name,
                "given_name": obj.givenName,
                "family_name": obj.familyName,
                "additional_name": obj.additionalName,
                "aliases": obj.alternateName,
                "description": obj.description,
                "job_title": obj.jobTitle,
                "affiliations": affiliations,
                "alumni": alumni,
                "works_for": works_for,
                "research_areas": obj.researchAreas,
                "about": obj.about,
                "works": works,
            },
            numeric_features={
                "works_count": safe_float(obj.works_count),
                "cited_by_count": safe_float(obj.cited_by_count),
            },
            boolean_features={
                "has_identifier": bool(obj.identifier),
                "has_affiliation": bool(affiliations),
                "has_research_areas": bool(obj.researchAreas),
                "has_works": bool(works),
            },
        )


class ProjectRankingAdapter:
    """
    Ranking adapter for project search results represented as Project objects.

    Extracts project title/description, funding/status metadata and date/cost-like features.
    """

    category = "projects"

    def supports(self, obj: object) -> bool:
        return isinstance(obj, Project)

    def to_document(self, obj: Project) -> RankingDocument:
        funder = _name(obj.funder)
        sponsor = _name(obj.sponsor)
        source_org = _name(obj.sourceOrganization)
        source_names = _source_names(obj)

        return RankingDocument(
            id=obj.identifier or obj.url or hash_fallback(obj),
            category=self.category,
            raw=obj,
            fields={
                "identifier": obj.identifier,
                "name": obj.name,
                "title": obj.headline or obj.name or obj.alternativeHeadline,
                "aliases": obj.alternateName,
                "description": obj.abstract or obj.description or obj.text,
                "keywords": obj.keywords,
                "source": source_names or obj.originalSource,
                "type": obj.additionalType,
                "status": obj.status,
                "funding": obj.funding,
                "funder": funder,
                "sponsor": sponsor,
                "source_organization": source_org,
                "date_start": obj.dateStart,
                "date_end": obj.dateEnd,
                "duration": obj.duration,
                "currency": obj.currency,
                "publication": obj.publication,
                "language": obj.inLanguage,
            },
            numeric_features={
                "year": safe_year(obj.dateStart or obj.datePublished or obj.dateCreated),
                "total_cost": safe_float(obj.totalCost),
                "funded_amount": safe_float(obj.fundedAmount),
                "eu_contribution": safe_float(obj.eu_contribution),
            },
            boolean_features={
                "has_identifier": bool(obj.identifier),
                "has_description": bool(obj.abstract or obj.description or obj.text),
                "has_dates": bool(obj.dateStart or obj.dateEnd),
                "has_funding": bool(obj.funding or obj.funder or obj.fundedAmount or obj.eu_contribution),
            },
        )


class SchemaObjectRankingAdapter:
    """
    Generic adapter for categories without a dedicated ranking adapter.

    Extracts a conservative set of common text fields to give every category a stable
    baseline ranking instead of failing when no specialized adapter exists.
    Missing fields are treated as empty values.
    """

    def __init__(self, category: str) -> None:
        self.category = category

    def supports(self, obj: object) -> bool:
        return True

    def to_document(self, obj: object) -> RankingDocument:
        authors = _names(getattr(obj, "author", None))
        publisher = _name(getattr(obj, "publisher", None))
        source_names = _source_names(obj)

        fields = {
            "identifier": getattr(obj, "identifier", ""),
            "url": getattr(obj, "url", ""),
            "name": getattr(obj, "name", ""),
            "title": (
                getattr(obj, "headline", "")
                or getattr(obj, "name", "")
                or getattr(obj, "alternativeHeadline", "")
            ),
            "aliases": _as_list(getattr(obj, "alternateName", None)),
            "description": (
                getattr(obj, "abstract", "")
                or getattr(obj, "description", "")
                or getattr(obj, "text", "")
            ),
            "keywords": _as_list(getattr(obj, "keywords", None)),
            "authors": authors,
            "source": source_names or getattr(obj, "originalSource", ""),
            "type": getattr(obj, "additionalType", ""),
            "publication": getattr(obj, "publication", ""),
            "publisher": publisher,
            "language": _as_list(getattr(obj, "inLanguage", None)),
            "license": getattr(obj, "license", ""),
            "version": getattr(obj, "version", ""),
            "status": getattr(obj, "status", ""),
            "location": getattr(obj, "location", ""),
            "address": getattr(obj, "address", ""),
            "legal_name": getattr(obj, "legalName", ""),
        }

        return RankingDocument(
            id=getattr(obj, "identifier", "") or getattr(obj, "url", "") or hash_fallback(obj),
            category=self.category,
            raw=obj,
            fields=fields,
            numeric_features={
                "citation_count": safe_float(getattr(obj, "citationCount", 0)),
                "reference_count": safe_float(getattr(obj, "referenceCount", 0)),
                "year": safe_year(
                    getattr(obj, "datePublished", "")
                    or getattr(obj, "dateCreated", "")
                    or getattr(obj, "dateStart", "")
                ),
            },
            boolean_features={
                "has_identifier": bool(getattr(obj, "identifier", "")),
                "has_description": bool(fields["description"]),
                "has_url": bool(getattr(obj, "url", "")),
            },
        )


def safe_float(value: Any) -> float | None:
    if value in (None, "", [], {}):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        pass

    try:
        cleaned = re.sub(r"[^0-9.\-]", "", str(value))
        return float(cleaned) if cleaned else None
    except (TypeError, ValueError):
        return None


def safe_year(value: Any) -> float | None:
    if value in (None, "", [], {}):
        return None

    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    if not match:
        return None

    return float(match.group(0))


def hash_fallback(obj: object) -> str:
    digest = hashlib.sha1(str(obj).encode("utf-8", errors="ignore")).hexdigest()
    return digest[:16]


def _name(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return value
    return getattr(value, "name", "") or str(value)


def _names(value: Any) -> list[str]:
    return [name for item in _as_list(value) if (name := _name(item))]


def _titles(value: Any) -> list[str]:
    titles = []
    for item in _as_list(value):
        title = (
            getattr(item, "headline", "")
            or getattr(item, "name", "")
            or getattr(item, "alternativeHeadline", "")
            or getattr(item, "title", "")
        )
        if title:
            titles.append(title)
    return titles


def _source_names(obj: object) -> list[str]:
    source_names = []
    for source in _as_list(getattr(obj, "source", None)):
        name = source if isinstance(source, str) else getattr(source, "name", "")
        if name:
            source_names.append(name)
    return list(dict.fromkeys(source_names))


def _as_list(value: Any) -> list[Any]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]
