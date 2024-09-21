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
def get_publication(source: str, doi: str, publications):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-endpoint', ''),
                                                    doi=doi)
    
    search_result = search_result.get('message',{})
    
    publication = Article()  
    title = search_result.get("title")        
    publication.name = utils.remove_html_tags(title[0])      
    publication.identifier = search_result.get("DOI", "").replace("https://doi.org/", "") 
    publication.abstract = utils.remove_html_tags(search_result.get("abstract", "")) 
    publication.publication = search_result.get("publisher", "")
    licenses = search_result.get("license", [])
    if len(licenses) > 0:
        publication.license = licenses[0].get('URL',"")
    publication.additionalType = search_result.get("type", "")
    publication.referenceCount = search_result.get("reference-count", "")
    publication.citationCount = search_result.get("is-referenced-by-count", "")

    authors = search_result.get("author", [])                        
    for author in authors:
        _author = Author()
        _author.type = 'Person'
        _author.name = author.get("given", "") + " " + author.get("family", "")
        _author.identifier = author.get("orcid", "")                            
        publication.author.append(_author)

    # references = search_result.get("reference", [])                        
    # for reference in references:
    #     referenced_publication = Article() 
    #     referenced_publication.identifier = reference.get("DOI", "") 
    #     structured_reference_text = []  
    #     structured_reference_text.append(reference.get("author", "")) 
    #     reference_year = reference.get("year", "")
    #     if reference_year  != "":
    #         structured_reference_text.append("(" + reference_year + ")")
    #     structured_reference_text.append(reference.get("article-title", ""))
    #     structured_reference_text.append(reference.get("series-title", ""))
    #     structured_reference_text.append(reference.get("journal-title", ""))
    #     structured_reference_text.append(reference.get("unstructured", ""))        
    #     referenced_publication.text = ('. ').join(structured_reference_text)
    #     publication.reference.append(referenced_publication)     
    
    publications.append(publication)

@utils.handle_exceptions
def get_publication_references(source: str, doi: str):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-references-endpoint', ''),
                                                    doi=doi)
    
    search_result = search_result.get('message',{})
    
    publication = Article()  
    references = search_result.get("reference", [])                        
    for reference in references:
        referenced_publication = Article() 
        referenced_publication.identifier = reference.get("DOI", "") 
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
        publication.reference.append(referenced_publication)     
    
    return publication
    