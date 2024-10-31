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
    process_search_results(source, results, search_result)        
    
def process_search_results(source: str, results, search_result):     
    total_records_found = search_result['meta']['count']
    hits = search_result.get("results", [])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")        

    if int(total_hits) > 0:    
        for hit in hits:                    
            
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
            # publication.publication = hit.get("primary_location", {}).get("source", {}).get("display_name", "")

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
                publication.author.append(_author)

            # getattr(publication, "source").clear()
            _source = thing()
            _source.name = 'OPENALEX'
            _source.identifier = hit.get("id", "").replace("https://openalex.org/", "") # remove the base url and only keep the ID
            _source.url = hit.get("id", "") # not a valid url, openalex is currently working on thier web interface.                                              
            publication.source.append(_source)

            if resource_type.upper() in ('ARTICLE', 'PREPRINT') and publication.identifier != "":
                results['publications'].append(publication)  
            else:
                results['others'].append(publication) 

@utils.handle_exceptions
def get_publications(source: str, url: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                    search_term="",
                                                    failed_sources=failed_sources,
                                                    url=url)
    process_search_results(source, results, search_result) 
    
@utils.handle_exceptions
def get_publication(source: str, doi: str, publications):

    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-endpoint', ''),
                                                    doi=doi)
    
    publication = Article()   
    publication.name = utils.remove_html_tags(search_result.get("title", ""))  
    publication.url = search_result.get("id", "") # not a valid url, openalex is currently working on their web interface.
    publication.identifier = search_result.get("doi", "").partition('doi.org/')[2]
    publication.datePublished = search_result.get("publication_date", "") 
    publication.inLanguage.append(search_result.get("language", ""))
    publication.license = search_result.get("primary_location", {}).get("license", "")
    publication.publication = search_result.get("primary_location", {}).get("source", {}).get("display_name", "")

    abstract_inverted_index = search_result.get("abstract_inverted_index", {})
    publication.description = utils.generate_string_from_keys(abstract_inverted_index) # Generate the string using keys from the dictionary
    publication.abstract = publication.description

    authorships = search_result.get("authorships", [])                        
    for authorship in authorships:

        author = authorship.get("author", {})

        _author = Author()
        _author.type = 'Person'
        _author.name = author.get("display_name", "")
        _author.identifier = author.get("orcid", "")                            
        publication.author.append(_author)
    
    keywords = search_result.get("keywords", [])                        
    for keyword in keywords:
        publication.keywords.append(keyword.get("display_name", "") )            
    
    publications.append(publication)