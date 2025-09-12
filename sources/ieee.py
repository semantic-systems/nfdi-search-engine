from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app
from datetime import datetime
from dateutil import parser

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 

    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources) 

    total_records = search_result.get("total_records", "")
    if int(total_records) == 0:
        utils.log_event(type="info", message=f"{source} - {total_records} records matched;")
    else:
        hits = search_result['articles']
        total_hits = len(hits)     
        utils.log_event(type="info", message=f"{source} - {total_records} records matched; pulled top {total_hits}")

        for hit in hits:
            digitalObj = map_digital_obj(source, hit) 
            results['publications'].append(digitalObj)   


# @utils.handle_exceptions
def map_digital_obj(source: str, hit: dict) -> Article:
    publication = Article()   
    publication.name = hit.get("title", "")             
    publication.url = hit.get("html_url", "")
    publication.identifier = hit.get("doi", "")
    publication.datePublished = datetime.strftime(parser.parse(hit.get("insert_date", "")), '%Y-%m-%d') 
    publication.license = hit.get("access_type", "")
    publication.publication = hit.get('publisher', '')
    publication.description = utils.remove_html_tags(hit.get('abstract', ''))
    publication.abstract = publication.description
    publication.encoding_contentUrl= hit.get('pdf_url', '')

    authors = hit.get("authors", {}).get("authors", [])                        
    for author in authors:
        _author = Author()
        _author.additionalType = 'Person'
        _author.name = author.get("full_name", "")
        _author.identifier = author.get("id", "") # ieee id of the author
        author_source = thing(
            name=source,
            identifier=_author.identifier,
        )
        _author.source.append(author_source)
        publication.author.append(_author)    

    _source = thing()
    _source.name = source
    _source.identifier = hit.get("article_number", "")
    _source.url = hit.get("html_url", "")                         
    publication.source.append(_source) 

    return publication    


@utils.handle_exceptions
def get_publication(source: str, doi: str, source_id: str, publications): 
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-endpoint', ''),
                                                    identifier=doi)
    
    if search_result:
        if len(search_result.get('articles',[])) > 0:
            hit = search_result['articles'][0]
            digitalObj = map_digital_obj(source, hit)
            publications.append(digitalObj)