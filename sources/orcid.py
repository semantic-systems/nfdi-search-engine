from objects import Author, thing, Organization
from sources import data_retriever
from typing import Iterable, Dict, Any
import utils
from main import app

from sources.base import BaseSource


class ORCID(BaseSource):

    SOURCE = 'ORCID'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(source=self.SOURCE, 
                                                    base_url=app.config['DATA_SOURCES'][self.SOURCE].get('search-endpoint', ''),
                                                    search_term=search_term,
                                                    failed_sources=failed_sources)

        return search_result
    

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        if raw is None:
            return []

        records_found = raw.get('num-found', 0)
        authors = raw.get('expanded-result', None)
        
        if records_found > 0 and authors:
            utils.log_event(type="info", message=f"{self.SOURCE} - {records_found} records matched; pulled top {len(authors)}")
            return authors
        
        return []
    

    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        authorObj = Author()
        authorObj.identifier = hit.get('orcid-id', '')
        given_names = hit.get('given-names', '')
        family_names = hit.get('family-names', '')
        authorObj.name = given_names + " " + family_names
        authorObj.additionalType = 'Person'
        
        institution = hit.get('institution-name', [])
        for inst in institution:
            authorObj.affiliation.append(Organization(name=inst))
        
        authorObj.works_count = ''
        authorObj.cited_by_count = ''

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get('orcid-id', '')
        _source.url = 'https://orcid.org/' + hit.get('orcid-id', '')
        authorObj.source.append(_source)

        return authorObj
    

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)

        if raw is None:
            return

        hits = self.extract_hits(raw)

        for hit in hits:
            authorObj = self.map_hit(hit)
            results['researchers'].append(authorObj)


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search ORCID researchers.
    """
    ORCID().search(source, search_term, results, failed_sources)
