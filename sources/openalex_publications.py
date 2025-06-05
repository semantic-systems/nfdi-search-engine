from objects import thing, Article, Author, CreativeWork
from sources import data_retriever
import utils
from main import app
from typing import Union

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                    search_term=search_term,
                                                    failed_sources=failed_sources) 
    process_search_results(source, results, search_result)        
    
def process_search_results(source: str, results, search_result):     
    total_records_found = search_result['meta']['count']
    hits = search_result.get("results", [])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")        

    if int(total_hits) > 0:    
        for hit in hits:  
            resource_type = hit.get("type", "")
            digitalObj = map_digital_obj(source, hit)
            if resource_type.upper() in ('ARTICLE', 'PREPRINT') and digitalObj.identifier != "":
                results['publications'].append(digitalObj)  
            else:
                results['others'].append(digitalObj) 


# @utils.handle_exceptions
def map_digital_obj(source: str, hit: dict) -> Union[Article, CreativeWork]:
    resource_type = hit.get("type", "")
    if resource_type.upper() in ('ARTICLE', 'PREPRINT'):
        publication = Article() 
    else:
        publication = CreativeWork() 

    publication.additionalType = resource_type
    publication.name = utils.remove_html_tags(hit.get("title", ""))       
    publication.url = hit.get("id", "") # not a valid url, openalex is currently working on their web interface.
    publication.identifier = hit.get("doi", "").replace("https://doi.org/", "")
    publication.datePublished = hit.get("publication_date", "") 
    publication.inLanguage.append(hit.get("language", ""))
    publication.license = hit.get("primary_location", {}).get("license", "")
    publication.publication = hit.get("primary_location", {}).get("source", {}).get("display_name", "")

    abstract_inverted_index = hit.get("abstract_inverted_index", {})
    publication.description = utils.generate_string_from_keys(abstract_inverted_index) # Generate the string using keys from the dictionary
    publication.abstract = publication.description

    authorships = hit.get("authorships", [])                        
    for authorship in authorships:
        author = authorship.get("author", {})
        _author = Author()
        _author.type = 'Person'
        _author.name = author.get("display_name", "")
        _author.identifier = author.get("orcid", "")    
        
        author_source = thing(
            name=source,
            identifier=_author.identifier,
        )
        _author.source.append(author_source)
                                
        publication.author.append(_author)
    
    keywords = hit.get("keywords", [])                        
    for keyword in keywords:
        publication.keywords.append(keyword.get("display_name", "") )  

    _source = thing()
    _source.name = source
    _source.identifier = hit.get("id", "").replace("https://openalex.org/", "") # remove the base url and only keep the ID
    _source.url = hit.get("id", "") # not a valid url, openalex is currently working on thier web interface.                                              
    publication.source.append(_source)

    return publication


@utils.handle_exceptions
def get_publications(source: str, url: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                    search_term="",
                                                    failed_sources=failed_sources,
                                                    url=url)
    process_search_results(source, results, search_result) 
    
@utils.handle_exceptions
def get_publication(source: str, doi: str, source_id: str, publications):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-endpoint', ''),
                                                    identifier="https://doi.org/"+doi)
    if search_result:
        digitalObj = map_digital_obj(source, search_result)
        publications.append(digitalObj)   