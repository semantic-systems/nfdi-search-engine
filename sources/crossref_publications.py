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
    hits = search_result['message'].get("items", [])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}") 

    for hit in hits:    
        digitalObj = map_digital_obj(source, hit)
        results['publications'].append(digitalObj)   

@utils.handle_exceptions
def map_digital_obj(source: str, hit: dict) -> Article:
    publication = Article() 
    publication.additionalType = hit.get("type", "")
    titles = hit.get("title", [])    
    if len(titles) > 0:
        publication.name = utils.remove_html_tags(titles[0])       
    publication.url = hit.get("URL", "")
    publication.identifier = hit.get("DOI", "").replace("https://doi.org/", "")
    publication.datePublished = hit.get("created", {}).get("date-time","") 
    publication.inLanguage.append(hit.get("language", ""))
    licenses = hit.get("license", [])
    if len(licenses) > 0:
        publication.license = licenses[0].get("URL", "")
    publication.publication = hit.get("publisher", "")

    publication.description = utils.remove_html_tags(hit.get("abstract",""))
    publication.abstract = publication.description

    publication.referenceCount = hit.get("reference-count", "")
    publication.citationCount = hit.get("is-referenced-by-count", "")

    authorships = hit.get("author", [])                        
    for authorship in authorships:
        _author = Author()
        _author.type = 'Person'
        _author.name = authorship.get("given", "") + " " + authorship.get("family", "")
        _author.identifier = authorship.get("orcid", "")                            
        publication.author.append(_author)
    
    _source = thing()
    _source.name = source
    _source.identifier = publication.identifier
    _source.url = publication.url                                          
    publication.source.append(_source)

    return publication


@utils.handle_exceptions
def get_publication(source: str, doi: str, source_id: str, publications):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-endpoint', ''),
                                                    identifier=doi)
    
    if search_result:
        search_result = search_result.get('message',{})
        digitalObj = map_digital_obj(source, search_result)        
        publications.append(digitalObj)

@utils.handle_exceptions
def get_publication_references(source: str, doi: str):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-references-endpoint', ''),
                                                    identifier=doi)
    if search_result:
        search_result = search_result.get('message',{})
        digitalObj = map_digital_obj(source, search_result)    
        
        references = search_result.get("reference", [])                        
        for reference in references:
            referenced_publication = Article() 
            referenced_publication.identifier = reference.get("DOI", "") 

            _source = thing()
            _source.name = source
            _source.identifier = referenced_publication.identifier
            _source.url = referenced_publication.url                                          
            referenced_publication.source.append(_source)

            structured_reference_text = []  
            structured_reference_text.append(reference.get("author", "")) 
            reference_year = reference.get("year", "")
            if reference_year  != "":
                structured_reference_text.append("(" + reference_year + ")")
            structured_reference_text.append(reference.get("article-title", ""))
            structured_reference_text.append(reference.get("series-title", ""))
            structured_reference_text.append(reference.get("journal-title", ""))
            structured_reference_text.append(reference.get("unstructured", ""))        
            referenced_publication.text = ('. ').join(filter(None, structured_reference_text))
            digitalObj.reference.append(referenced_publication)     
        
        return digitalObj
    