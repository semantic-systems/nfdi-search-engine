from nfdi_search_engine.common.models.objects import thing, Article, Author
from sources import data_retriever
from typing import Iterable, Dict, Any, List
from config import Config

from sources.base import BaseSource


class DBLP_Publications(BaseSource):

    SOURCE = 'dblp - Publications'

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """

        search_result = data_retriever.retrieve_data(
            base_url=Config.DATA_SOURCES[self.SOURCE].get(
                'search-endpoint', ''),
            search_term=search_term,
        )

        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        hits = raw['result']['hits']
        total_records_found = hits['@total']
        total_hits = hits['@sent']

        self.log_event(type="info", message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}")

        return hits

    def map_hit(self, hit: Dict[str, Any]) -> Article:
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        publication = Article()

        info = hit['info']
        publication.name = info.get("title", "")
        publication.url = info.get("url", "")
        publication.identifier = info.get("doi", "")
        publication.datePublished = info.get("year", "")
        publication.license = info.get("access", "")
        publication.publication = info.get("venue", "")

        authors = info.get("authors", {}).get("author", [])
        if isinstance(authors, dict):
            _author = Author()
            _author.additionalType = 'Person'
            _author.name = authors.get("text", "")
            # ideally this pid should be stored somewhere else
            _author.identifier = authors.get("@pid", "")
            publication.author.append(_author)

        if isinstance(authors, list):
            for author in authors:
                _author = Author()
                _author.additionalType = 'Person'
                _author.name = author.get("text", "")
                # ideally this pid should be stored somewhere else
                _author.identifier = author.get("@pid", "")

                author_source = thing(
                    name=self.SOURCE,
                    identifier=_author.identifier,
                )
                _author.source.append(author_source)

                publication.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("@id", "")
        _source.url = info.get("url", "")
        publication.source.append(_source)

        return publication

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term)
        hits = self.extract_hits(raw)

        for hit in hits:
            digitalObj = self.map_hit(hit)

            if digitalObj.identifier != "":
                results['publications'].append(digitalObj)
            else:
                results['others'].append(digitalObj)


def search(search_term: str, results: dict, tracking=None):
    """
    Entrypoint to search DBLP publications.
    """
    DBLP_Publications(tracking).search(search_term, results)
