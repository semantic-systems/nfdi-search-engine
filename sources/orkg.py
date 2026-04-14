from nfdi_search_engine.common.models.objects import thing, Article, Author
from sources import data_retriever
from config import Config
import requests
from typing import Iterable, Dict, Any, List

from sources.base import BaseSource

class ORKG(BaseSource):

    SOURCE = 'ORKG'

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(
            base_url=Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', ''),
            search_term=search_term,
        )

        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        meta = raw['page']
        total_hits = meta['total_elements']
        total_records_pulled = meta['size']
        self.log_event(type="info", message=f"{self.SOURCE} - {total_hits} records matched; pulled top {total_records_pulled}")
        hits = raw['content']
        return hits

    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """

        details_api = "https://orkg.org/api/"       # should be moved to config.py
        author_url = "https://orkg.org/author/"     # should be moved to config.py

        id = hit.get('id', None)
        classes = hit.get('classes', [])

        if 'Paper' in classes:
            api_url = details_api + 'papers/' + id
            response = requests.get(api_url)
            paper = response.json()

            publication = Article()
            publication.name = paper.get('title', '')
            publication.url = api_url

            identifiers = paper.get('identifiers', {})
            dois = identifiers.get('doi', [])
            if len(dois) > 0:
                publication.identifier = dois[0]
            
            month = paper.get('publication_info', {}).get('published_month', None)
            year = paper.get('publication_info', {}).get('published_year', None)
            if month is not None and year is not None:
                publication.datePublished = str(month) + '/' + str(year)
            elif year is not None:
                publication.datePublished = str(year)

            if paper.get('authors', []):
                for item in paper.get('authors', []):
                    author = Author()
                    author.additionalType = 'Person'
                    author.name = item.get('name', '')
                    author.identifier = item.get('identifiers', {}).get('orcid', '')
                    if item.get('id', ''):
                        author.url = author_url + item.get('id')
                    publication.author.append(author)
            
            _source = thing()
            _source.name = self.SOURCE
            _source.identifier = id
            _source.url = api_url                        
            publication.source.append(_source)

            return publication

        return None

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term)
        hits = self.extract_hits(raw)

        for hit in hits:
            publication = self.map_hit(hit)

            if publication:
                results['publications'].append(publication)


def search(search_term: str, results, tracking=None):
    """
    Entrypoint to search ORKG publications.
    """
    ORKG(tracking).search(search_term, results)
