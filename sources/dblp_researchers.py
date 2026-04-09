import requests
from nfdi_search_engine.common.models.objects import thing, Article, Author, Organization
from typing import Iterable, Dict, Any, List
import logging
from sources import data_retriever
from config import Config

from sources.base import BaseSource


class DBLP_Researchers(BaseSource):

    SOURCE = 'dblp-Researchers'

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

        if int(total_hits) > 0:
            hits = hits['hit']
            return hits
        return None

    def map_hit(self, hit: Dict[str, Any]) -> Author:

        author = Author()
        info = hit.get('info', {})

        author.name = info.get('author', '')
        alias = info.get('aliases', {}).get('alias', '')
        if isinstance(alias, str):
            author.alternateName.append(alias)
        if isinstance(alias, list):
            for _alias in alias:
                author.alternateName.append(_alias)

        affiliations = info.get('notes', {}).get('note', {})
        if isinstance(affiliations, list):
            for affiliation in affiliations:
                if affiliation.get('@type', '') == 'affiliation':
                    _organization = Organization()
                    _organization.name = affiliation.get('text', '')
                    author.affiliation.append(_organization)
        if isinstance(affiliations, dict):
            if affiliations.get('@type', '') == 'affiliation':
                _organization = Organization()
                _organization.name = affiliations.get('text', '')
                author.affiliation.append(_organization)

        # author.works_count = ''
        # author.cited_by_count = ''

        _source = thing()
        _source.name = 'DBLP'
        _source.identifier = hit.get("@id", "")
        _source.url = info.get("url", "")
        author.source.append(_source)

        return author

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term)
        hits = self.extract_hits(raw)

        if hits:
            for hit in hits:
                author = self.map_hit(hit)
                results['researchers'].append(author)


def search(search_term: str, results: dict, tracking=None):
    """
    Entrypoint to search for DBLP researchers.
    """
    DBLP_Researchers(tracking).search(search_term, results)
