from objects import thing, Article, Author
from typing import Iterable, Dict, Any, List
from sources import data_retriever
import utils
from main import app

from sources.base import BaseSource

class DBLP_Venues(BaseSource):

    SOURCE = 'DBLP - VENUES'

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
    def map_hit(self, source_name: str, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        venue = thing()

        info = hit['info']

        venue.name = info.get("venue", "")
        venue.alternateName = info.get("acronym", "")
        venue.url = info.get("url", "")
        venue.additionalType = info.get("type", "")
        
        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("@id", "")
        _source.url = info.get("url", "")                         
        venue.source.append(_source)

        return venue
    
    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        if hits:
            for hit in hits:
                venue = self.map_hit(hit)
                results['events'].append(venue)

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search DBLP venues.
    """
    DBLP_Venues().search(source, search_term, results, failed_sources)