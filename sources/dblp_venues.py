from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)      

    hits = search_result['result']['hits']
    total_records_found = hits['@total']
    total_hits = hits['@sent']

    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")

    if int(total_hits) > 0:
        hits = hits['hit']  
        for hit in hits:

            venue = thing()

            info = hit['info']

            venue.name = info.get("venue", "")
            venue.alternateName = info.get("acronym", "")
            venue.url = info.get("url", "")
            venue.additionalType = info.get("type", "")
            
            _source = thing()
            _source.name = source
            _source.identifier = hit.get("@id", "")
            _source.url = info.get("url", "")                         
            venue.source.append(_source)

            results['events'].append(venue)
            