from objects import thing, Article, Author, CreativeWork
from sources import data_retriever
from sources.base import BaseSource
from config import Config
from typing import Union, Dict, Any, List, Iterable
import utils

SOURCE = "OPENALEX - Publications"

class OpenAlexPublications(BaseSource):
    """
    Implements the BaseSource interface for OpenAlex Publications.
    """

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Hit the OpenAlex search endpoint with the given search term and return the JSON response.
        """

        base_url = Config.DATA_SOURCES[SOURCE].get("search-endpoint", "")

        response =  data_retriever.retrieve_data(
            source=SOURCE,
            base_url=base_url,
            search_term=search_term,
            failed_sources=[],
        )

        return response or {}


    def extract_hits(self, raw) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response.
        """
        return raw.get("results", []) or []

    def map_hit(self, source: str, hit: Dict[str, Any]) -> Union[Article, CreativeWork]:
        """
        Map a single hit dict from OpenAlex to an Article or CreativeWork object.
        """

        resource_type = (hit.get("type") or "").upper()

        if resource_type in ("ARTICLE", "PREPRINT"):
            publication = Article()
        else:
            publication = CreativeWork()

        publication.additionalType = hit.get("type", "")
        publication.name = utils.remove_html_tags(hit.get("title", "") or "")

        # OpenAlex "id" is their work URL
        _id = hit.get("id", "") or ""
        publication.url = _id
        publication.identifier = (hit.get("doi", "") or "").replace("https://doi.org/", "")
        publication.datePublished = hit.get("publication_date", "") or ""

        lang = hit.get("language", "")
        if lang:
            publication.inLanguage.append(lang)

        primary_location = (hit.get("primary_location") or {})  # may be None
        publication.license = primary_location.get("license", "") or ""
        publication.publication = ((primary_location.get("source") or {}).get("display_name", "") or "")

        abstract_inverted_index = (hit.get("abstract_inverted_index") or {})
        publication.description = utils.generate_string_from_keys(abstract_inverted_index)
        publication.abstract = publication.description

        publication.encoding_contentUrl = primary_location.get("pdf_url", "") or ""

        # authors
        for authorship in (hit.get("authorships") or []):
            author = (authorship.get("author") or {})
            _author = Author()
            _author.additionalType = "Person"
            _author.name = author.get("display_name", "") or ""
            _author.identifier = author.get("orcid", "") or ""

            _author.source.append(
                thing(
                    name=source,
                    identifier=_author.identifier,
                )
            )

            publication.author.append(_author)

        # keywords
        for keyword in (hit.get("keywords") or []):
            publication.keywords.append(keyword.get("display_name", "") or "")

        # source
        _source = thing()
        _source.name = source
        _source.identifier = _id.replace("https://openalex.org/", "")
        _source.url = _id
        publication.source.append(_source)

        return publication

    @utils.handle_exceptions
    def search(self, source: str, search_term: str, results: Dict[str, List], failed_sources: List[str]) -> None:
        """
        Search OpenAlex for the given term and append mapped results to the results dict.
        """

        # 1. fetch the raw json response
        raw = self.fetch(search_term)

        # 2. extract the hits
        hits = list(self.extract_hits(raw))

        # log the number of records found
        total_records_found = (
            (raw.get("meta", {}) or {}).get("count")
            or len(hits)
            or 0
        )
        utils.log_event(
            type="info",
            message=f"{source} - {total_records_found} records matched; pulled top {len(hits)}",
        )

        # 3. map each hit and append to results
        for hit in hits:
            obj = self.map_hit(source, hit)
            if (hit.get("type", "") or "").upper() in ("ARTICLE", "PREPRINT") and getattr(obj, "identifier", ""):
                results["publications"].append(obj)
            else:
                results["others"].append(obj)


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search OpenAlex publications.
    """
    OpenAlexPublications().search(source, search_term, results, failed_sources)

@utils.handle_exceptions
def get_publication(source: str, doi: str, source_id: str, publications):
    """
    Fetch a single object by DOI and map it.
    """
    base_url = Config.DATA_SOURCES[SOURCE].get("get-publication-endpoint", "")
    search_result = data_retriever.retrieve_object(
        source=source,
        base_url=base_url,
        identifier="https://doi.org/" + doi,
    )
    if search_result:
        obj = OpenAlexPublications().map_hit(source, search_result)
        publications.append(obj)