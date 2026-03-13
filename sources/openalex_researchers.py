from nfdi_search_engine.common.models.objects import thing, Author, Organization
from sources import data_retriever
from sources.base import BaseSource
from typing import Iterable, Dict, Any, List
from config import Config
from sources import openalex_publications


class OpenAlexResearchers(BaseSource):
    """
    Implements the BaseSource interface for OpenAlex Researchers.
    """

    def fetch(self, search_term: str, failed_sources: List[str], source_name: str = None) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        # Use source_name if provided, otherwise fall back to app.config
        if source_name:
            base_url = Config.DATA_SOURCES[source_name].get("search-endpoint", "")
            source = source_name
        else:
            # Fallback for backward compatibility
            base_url = Config.DATA_SOURCES.get("OPENALEX - Researchers", {}).get("search-endpoint", "")
            source = "OPENALEX - Researchers"
        
        search_result = data_retriever.retrieve_data(
            source=source,
            base_url=base_url,
            search_term=search_term,
            failed_sources=failed_sources
        )
        
        return search_result or {}

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        hits = raw.get("results", [])
        
        return hits

    def map_hit(self, source_name: str, hit: Dict[str, Any]) -> Author:
        """
        Map a single hit dict from the source to an Author object.
        """
        author = Author()
        
        # Identifier (ORCID)
        author.identifier = hit.get("ids", {}).get("orcid", "").replace("https://orcid.org/", "")
        author.additionalType = "Person"

        # Name
        author.name = hit.get("display_name", "")
        
        # Alternate names
        alias = hit.get("display_name_alternatives", [])
        if isinstance(alias, str):
            author.alternateName.append(alias)
        elif isinstance(alias, list):
            for _alias in alias:
                author.alternateName.append(_alias)

        # Affiliations
        affiliations = hit.get("affiliations", [])
        if isinstance(affiliations, list):
            for affiliation in affiliations:
                institution = affiliation.get("institution", {})
                if isinstance(institution, dict):
                    _organization = Organization()
                    _organization.name = institution.get("display_name", "")
                    years = affiliation.get("years", [])
                    if len(years) > 1:
                        _organization.keywords.append(f"{years[-1]}-{years[0]}")
                    elif len(years) == 1:
                        _organization.keywords.append(f"{years[0]}")
                    author.affiliation.append(_organization)

        # Research areas (topics)
        topics = hit.get("x_concepts", [])
        if isinstance(topics, list):
            for topic in topics:
                name = topic.get("display_name", "")
                if name:
                    author.researchAreas.append(name)

        # Works count and citation count
        author.works_count = hit.get("works_count", "")
        author.cited_by_count = hit.get("cited_by_count", "")

        # Source information
        _source = thing()
        _source.name = source_name
        openalex_id = hit.get("ids", {}).get("openalex", "").replace("https://openalex.org/", "")
        _source.identifier = openalex_id
        _source.url = hit.get("ids", {}).get("openalex", "")
        author.source.append(_source)

        return author

    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        # 1. Fetch the raw json response
        raw = self.fetch(search_term, failed_sources, source_name)
        
        if not raw:
            return

        # 2. Extract the hits
        hits = self.extract_hits(raw)
        
        # Log the number of records found
        total_records_found = raw.get("meta", {}).get("count", 0) if raw.get("meta") else 0
        total_hits = len(list(hits)) if not isinstance(hits, list) else len(hits)
        self.log_event(
            type="info",
            message=f"{source_name} - {total_records_found} records matched; pulled top {total_hits}"
        )

        # 3. Map each hit and append to results
        for hit in hits:
            author = self.map_hit(source_name, hit)
            results["researchers"].append(author)


def search(source: str, search_term: str, results, failed_sources, tracking=None):
    """
    Entrypoint to search OpenAlex researchers.
    """
    OpenAlexResearchers(tracking).search(source, search_term, results, failed_sources)


def get_researcher(source: str, orcid: str, source_id: str, researchers, tracking=None):
    """
    Fetch a single researcher by ORCID and map it to an Author object.
    """
    if not orcid.startswith("https://orcid.org"):
        orcid = "https://orcid.org/" + orcid

    hit = data_retriever.retrieve_object(
        source=source,
        base_url=Config.DATA_SOURCES[source].get("get-researcher-endpoint", ""),
        identifier=orcid
    )
    
    if not hit:
        return

    researcher = Author()
    researcher.url = orcid
    researcher.identifier = hit.get("ids", {}).get("orcid", "").replace("https://orcid.org/", "")
    researcher.name = hit.get("display_name", "")
    
    # Alternate names
    alias = hit.get("display_name_alternatives", [])
    if isinstance(alias, str):
        researcher.alternateName.append(alias)
    elif isinstance(alias, list):
        for _alias in alias:
            researcher.alternateName.append(_alias)

    # Affiliations
    affiliations = hit.get("affiliations", [])
    if isinstance(affiliations, list):
        for affiliation in affiliations:
            institution = affiliation.get("institution", {})
            if isinstance(institution, dict):
                _organization = Organization()
                _organization.name = institution.get("display_name", "")
                years = affiliation.get("years", [])
                if len(years) > 1:
                    _organization.keywords.append(f"{years[-1]}-{years[0]}")
                elif len(years) == 1:
                    _organization.keywords.append(f"{years[0]}")
                researcher.affiliation.append(_organization)

    # Research areas (topics)
    topics = hit.get("topics", [])
    if isinstance(topics, list):
        for topic in topics:
            name = topic.get("display_name", "")
            if name:
                researcher.researchAreas.append(name)

    # Source information
    _source = thing()
    _source.name = source
    openalex_id = hit.get("ids", {}).get("openalex", "").replace("https://openalex.org/", "")
    _source.identifier = openalex_id
    researcher.source.append(_source)

    # Search OpenAlex for author's publications
    researcher_publications = {
        "publications": [],
        "others": [],
    }
    openalex_id_full = hit.get("id", "").replace("https://openalex.org/", "")
    url = Config.DATA_SOURCES[source].get("get-researcher-publications-endpoint", "") + openalex_id_full
    openalex_publications.get_publications("OPENALEX - Publications", url, researcher_publications, [], tracking=tracking)
    researcher.works.extend(researcher_publications["publications"])

    researchers.append(researcher)
