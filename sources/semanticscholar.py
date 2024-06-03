import requests
from objects import thing, Article, Author
import logging
import utils
from sources import data_retriever
import traceback
import time

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def get_recommendations_for_publication(doi: str):
     
    source = "SEMANTIC SCHOLAR recommendations"

    try:
        recommended_publications = []

        reAttemptFlag = True

        while(reAttemptFlag):
            # first retrieve semantic scholar paper id against the doi 
            search_result = data_retriever.retrieve_get_single_object(source=source, 
                                                        base_url=utils.config["publication_details_semanticscholar_publication"],
                                                        doi=doi)
            
            if type(search_result) != dict and int(search_result) == 429:
                reAttemptFlag = True
                print('Try again after 1-2 seconds')
                #force 1-2 seconds delay before two consecutive requests
                time.sleep(2)
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
                print('Try again after 1-2 seconds')
                #force 1-2 seconds delay before two consecutive requests
                time.sleep(2)
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
                    
        return recommended_publications

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')        
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())