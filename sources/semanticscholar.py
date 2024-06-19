import requests
from objects import thing, Article, Author
import logging
import utils
from sources import data_retriever
import traceback
import time
from random import randrange

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')



@utils.timeit
def get_recommendations_for_publication(doi: str):
     
    source = "SEMANTIC SCHOLAR recommendations"
    recommended_publications = []
    try:
        reAttemptFlag = True
        while(reAttemptFlag):
            # first retrieve semantic scholar paper id against the doi 
            search_result = data_retriever.retrieve_single_object(source=source, 
                                                        base_url=utils.config["publication_details_semanticscholar_publication"],
                                                        doi=doi)
            
            if type(search_result) != dict and int(search_result) == 429:
                reAttemptFlag = True
                print('Try again after few seconds')
                #force few seconds delay before two consecutive requests
                time.sleep(randrange(5))
            else:      
                reAttemptFlag = False      
                paper_id = search_result.get('paperId',"")
                print("paper_id:", paper_id)
                
        reAttemptFlag = True
        while(reAttemptFlag):
            # now pull recommendations with this paper id
            search_result = data_retriever.retrieve_data(source=source, base_url=utils.config["publication_details_semanticscholar_recommendations"],
                                                        search_term=paper_id+"?fields=title,publicationDate,externalIds&limit=10", results={} )#pass empty dict in the results

            if type(search_result) != dict and int(search_result) == 429:
                reAttemptFlag = True
                print('Try again after few seconds')
                #force few seconds delay before two consecutive requests
                time.sleep(randrange(5))
            else: 
                reAttemptFlag = False
                recommended_papers = search_result.get('recommendedPapers', [])
                for recommended_paper in recommended_papers:

                    publication = Article()  
                    publication.name = utils.remove_html_tags(recommended_paper.get("title", ""))
                    publication.identifier = recommended_paper.get("externalIds", {}).get("DOI", "")
                    publication.datePublished = recommended_paper.get("publicationDate", "")
                    
                    # make sure identifier/doi is not empty
                    if publication.identifier != "":
                        recommended_publications.append(publication)    

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')        
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())

    finally:
        return recommended_publications



@utils.timeit
def get_citations_for_publication(doi: str):
     
    source = "SEMANTIC SCHOLAR citations"
    citations_list = []
    try:        
        reAttemptFlag = True
        while(reAttemptFlag):
            # first retrieve semantic scholar paper id against the doi 
            search_result = data_retriever.retrieve_single_object(source=source, 
                                                        base_url=utils.config["publication_details_semanticscholar_publication"],
                                                        doi=doi+"?fields=citations.title,citations.year,citations.externalIds,citations.authors")
            
            if type(search_result) != dict and int(search_result) == 429:
                reAttemptFlag = True
                print('Try again after few seconds')
                #force few seconds delay before two consecutive requests
                time.sleep(randrange(5))           
            else: 
                reAttemptFlag = False
                citations = search_result.get('citations', [])
                for citation in citations:

                    publication = Article()  
                    publication.name = utils.remove_html_tags(citation.get("title", ""))
                    authors = citation.get("authors", [])                        
                    for author in authors:

                        _author = Author()
                        _author.type = 'Person'
                        _author.name = author.get("name", "")                         
                        publication.author.append(_author)

                    publication.identifier = citation.get("externalIds", {}).get("DOI", "")
                    publication.datePublished = citation.get("year", "")

                    _source = thing()
                    _source.name = 'SEMANTIC SCHOLAR'
                    publication.source.append(_source)
                    
                    citations_list.append(publication)   

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')        
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())    

    finally:
         return citations_list 