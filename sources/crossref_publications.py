from objects import thing, Article, Author, CreativeWork
from sources import data_retriever
import utils
from main import app

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                    search_term=search_term,
                                                    failed_sources=failed_sources) 
    total_records_found = search_result['message']['total-results']
    hits = search_result.get("items", [])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")        

    if int(total_hits) > 0:    
        for hit in hits:                    
            
            # resource_type = hit.get("type", "")

            # if resource_type.upper() in ('ARTICLE', 'PREPRINT'):
            #     publication = Article() 
            # else:
            #     publication = CreativeWork() 
            publication = Article() 
            publication.additionalType = hit.get("type", "")
            publication.name = utils.remove_html_tags(hit.get("title", ""))       
            publication.url = hit.get("url", "")
            publication.identifier = hit.get("DOI", "").replace("https://doi.org/", "")
            publication.datePublished = hit.get("created", {}).get("date-time","") 
            publication.inLanguage.append(hit.get("language", ""))
            publication.license = hit.get("license", [])[0].get("URL", "")
            publication.publication = hit.get("publisher", "")

            publication.description = utils.remove_html_tags(hit.get("abstract",""))
            publication.abstract = publication.description

            authorships = hit.get("author", [])                        
            for authorship in authorships:
                _author = Author()
                _author.type = 'Person'
                _author.name = authorship.get("given", "") + " " + authorship.get("family", "")
                _author.identifier = authorship.get("ORCID", "")                            
                publication.author.append(_author)
            
            _source = thing()
            _source.name = 'CROSSREF'
            _source.identifier = publication.identifier
            _source.url = publication.url                                          
            publication.source.append(_source)

            results['publications'].append(publication)  

@utils.handle_exceptions
def get_publication(source: str, doi: str):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-endpoint', ''),
                                                    doi=doi)
    
    search_result = search_result.get('message',{})
    
    publication = Article()   

    title = search_result.get("title")        
    publication.name = utils.remove_html_tags(title[0])      
    publication.identifier = search_result.get("DOI", "").replace("https://doi.org/", "") 
    publication.abstract = utils.remove_html_tags(search_result.get("abstract", "")) 

    references = search_result.get("reference", [])                        
    for reference in references:
        referenced_publication = Article() 
        referenced_publication.text = reference.get("unstructured", "")
        referenced_publication.identifier = reference.get("DOI", "")                            
        publication.citation.append(referenced_publication)     
    
    return publication

    