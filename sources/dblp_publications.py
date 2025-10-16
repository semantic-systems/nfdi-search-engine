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
                _author.identifier = authors.get("@pid", "") #ideally this pid should be stored somewhere else
                publication.author.append(_author)    

            if isinstance(authors, list):
                for author in authors:
                    _author = Author()
                    _author.additionalType = 'Person'
                    _author.name = author.get("text", "")
                    _author.identifier = author.get("@pid", "") #ideally this pid should be stored somewhere else
                    
                    author_source = thing(
                        name=source,
                        identifier=_author.identifier,
                    )
                    _author.source.append(author_source)

                    publication.author.append(_author)    

            _source = thing()
            _source.name = source
            _source.identifier = hit.get("@id", "")
            _source.url = info.get("url", "")                         
            publication.source.append(_source)

            if publication.identifier != "":
                results['publications'].append(publication)
            else:
                results['others'].append(publication)
