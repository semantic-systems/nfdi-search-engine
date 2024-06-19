import requests
from objects import thing, Article, Author
import logging
import utils
from sources import data_retriever
import traceback


# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def get_publication(doi: str):
     
    source = "CROSSREF Publication"

    try:
        search_result = data_retriever.retrieve_single_object(source=source, 
                                                     base_url=utils.config["publication_details_crossref_publications"],
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

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')        
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())