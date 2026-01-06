import requests
from objects import thing, Article, Author, Organization
from typing import Iterable, Dict, Any, List
import logging
import utils
from sources import data_retriever
import utils
from main import app

from sources.base import BaseSource

class DBLP_Researchers(BaseSource):

    SOURCE = 'dblp-Researchers'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(source=self.SOURCE, 
                                                    base_url=app.config['DATA_SOURCES'][self.SOURCE].get('endpoint', ''),
                                                    search_term=search_term,
                                                    failed_sources=failed_sources)  

        return search_result      

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """

        hits = raw['result']['hits']
        total_records_found = hits['@total']
        total_hits = hits['@sent']

        utils.log_event(type="info", message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}")

        if int(total_hits) > 0:
            hits = hits['hit']
            return hits
        return None
    
    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]) -> Author:
                
        author = Author()
        info = hit.get('info',{})

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
    
    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        if hits:
            for hit in hits:
                author = self.map_hit(hit)
                results['researchers'].append(author)

def search(source_name: str, search_term: str, results: dict, failed_sources: list):
    """
    Entrypoint to search for DBLP researchers.
    """
    DBLP_Researchers().search(source_name, search_term, results, failed_sources)