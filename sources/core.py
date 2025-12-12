from objects import thing, Article, Author, Organization
from sources import data_retriever
from config import Config
from typing import Iterable, Dict, Any, List
import utils
import requests
from main import app

from sources.base import BaseSource


class CORE(BaseSource):

    SOURCE = 'CORE'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        # we cannot use data_retriever.retrieve_data here because we need to send the request with an API key in the header
        # learn more: https://api.core.ac.uk/docs/v3#tag/Search
        limit = Config.NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT
        api_url = f'https://api.core.ac.uk/v3/search/works/?limit={limit}&q={search_term}&_exists_:doi'
        headers = {"Authorization":"Bearer " + Config.CORE_API_KEY}

        # send the request
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            search_result = response.json()
            return search_result
        
        failed_sources.append(self.SOURCE)
        return None
    

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """

        hits = raw['results']
        total_hits = raw['totalHits']
        total_results = len(hits)

        utils.log_event(type="info", message=f"{self.SOURCE} - {total_hits} records matched; pulled top {total_results}") 

        return hits
    

    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """

        publication = Article() 
        publication.additionalType = hit.get("documentType", "")
        publication.name = hit.get("title", "")

        # go through the links and find the one with type: display
        links = hit.get("links", {})
        for link in links:
            if link.get("type", "") == "display":
                publication.url = link.get("url", "")
                break
        
        publication.encoding_contentUrl = hit.get("downloadUrl", "")

        # publications may not always have a DOI!
        # if we don't find one, we do NOT create a result object for the hit
        if not hit.get("doi", None):
            print("No DOI found for publication:", publication.name)
            return None

        publication.identifier = hit.get("doi", "")
        publication.datePublished = hit.get("publishedDate", "")
        publication.inLanguage.append(hit.get("language", {}).get("code", ""))

        # abstracts may also be empty
        abstract = hit.get("abstract", "")
        if not abstract:
            abstract = ""

        publication.description = utils.remove_html_tags(abstract)
        publication.abstract = publication.description

        publication.citationCount = hit.get("citationCount", "")

        if hit.get("publisher", ""):
            _publisher = Organization()
            _publisher.name = hit.get("publisher", "")
            publication.publisher = _publisher

        authors = hit.get("authors", [])
        for author in authors:
            _author = Author()
            _author.additionalType = 'Person'
            _author.name = author.get("name", "")
            publication.author.append(_author)
        
        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = publication.identifier
        _source.url = publication.url
        publication.source.append(_source)

        return publication
    

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)

        if raw == None:
            return

        hits = self.extract_hits(raw)

        for hit in hits:
            digitalObj = self.map_hit(hit)

            # we only create a result object if we found a DOI, otherwise None
            if digitalObj:
                results['publications'].append(digitalObj)

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search CORE publications.
    """
    CORE().search(source, search_term, results, failed_sources)