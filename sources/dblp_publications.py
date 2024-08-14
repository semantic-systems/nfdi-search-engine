from objects import thing, Article, Author
from sources import data_retriever
import logging
import utils
from main import app

@utils.handle_exceptions
@utils.timeit
def search(source: str, search_term: str, results): 

    search_result = data_retriever.retrieve_data(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('endpoint', ''),
                                                    search_term=search_term,
                                                    results=results)        

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
                _author.type = 'Person'
                _author.name = authors.get("text", "")
                _author.identifier = authors.get("@pid", "") #ideally this pid should be stored somewhere else
                publication.author.append(_author)    

            if isinstance(authors, list):
                for author in authors:
                    _author = Author()
                    _author.type = 'Person'
                    _author.name = author.get("text", "")
                    _author.identifier = author.get("@pid", "") #ideally this pid should be stored somewhere else
                    publication.author.append(_author)    

            _source = thing()
            _source.name = 'DBLP'
            _source.identifier = hit.get("@id", "")
            _source.url = info.get("url", "")                         
            publication.source.append(_source)

            results['publications'].append(publication)    
