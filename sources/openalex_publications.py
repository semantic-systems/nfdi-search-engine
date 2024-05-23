import requests
from objects import thing, Article, Author
import logging
import utils
from sources import data_retriever
import traceback

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

def generate_string_from_keys(dictionary):
    keys_list = list(dictionary.keys())
    keys_string = " ".join(keys_list)
    return keys_string

@utils.timeit
def search(search_term: str, results):
    
    source = "OPENALEX Publications"

    try:
        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=utils.config["search_url_openalex_publications"],
                                                     search_term=search_term,
                                                     results=results)
        total_records_found = search_result['meta']['count']
        hits = search_result.get("results", [])
        total_hits = len(hits)
        logger.info(f'{source} - {total_records_found} records matched; pulled top {total_hits}') 

        if int(total_hits) > 0:    
            for hit in hits:
                    
                    publication = Article()   

                    publication.name = utils.remove_html_tags(hit.get("title", ""))       
                    publication.url = hit.get("id", "") # not a valid url, openalex is currently working on their web interface.
                    publication.identifier = hit.get("doi", "").replace("https://doi.org/", "")
                    publication.datePublished = hit.get("publication_date", "") 
                    publication.inLanguage.append(hit.get("language", ""))
                    publication.license = hit.get("primary_location", {}).get("license", "")
                    # publication.publication = hit.get("primary_location", {}).get("source", {}).get("display_name", "")

                    abstract_inverted_index = hit.get("abstract_inverted_index", {})
                    publication.description = generate_string_from_keys(abstract_inverted_index) # Generate the string using keys from the dictionary
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

                    results['publications'].append(publication)  
        
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())


@utils.timeit
def get_publication(doi: str):
     
    source = "OPENALEX Publication"

    try:
        search_result = data_retriever.retrieve_get_single_object(source=source, 
                                                     base_url=utils.config["publication_details_openalex_publications"],
                                                     doi=doi)
        
        publication = Article()   

        publication.name = utils.remove_html_tags(search_result.get("title", ""))  
        publication.url = search_result.get("id", "") # not a valid url, openalex is currently working on their web interface.
        publication.identifier = search_result.get("doi", "").replace("https://doi.org/", "")
        publication.datePublished = search_result.get("publication_date", "") 
        publication.inLanguage.append(search_result.get("language", ""))
        publication.license = search_result.get("primary_location", {}).get("license", "")
        publication.publication = search_result.get("primary_location", {}).get("source", {}).get("display_name", "")

        abstract_inverted_index = search_result.get("abstract_inverted_index", {})
        publication.description = generate_string_from_keys(abstract_inverted_index) # Generate the string using keys from the dictionary
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
        
        return publication

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')        
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())