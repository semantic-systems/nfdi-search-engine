from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app
import time
from random import randrange

@utils.handle_exceptions
def get_recommendations_for_publication(source: str, doi: str):     
    
    recommended_publications = []
    
    reAttemptFlag = True
    reAttemptCount = 0
    while(reAttemptFlag and reAttemptCount < 10):    
        # first retrieve semantic scholar paper id against the doi 
        # this end point will return semantic scholar paperId and the paper title
        search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('citations-endpoint', ''),
                                                    identifier=doi)
        
        if type(search_result) != dict:
            reAttemptFlag = True
            print('Try again for SS paper ID')            
            time.sleep(2) #force one second delay between two consecutive requests
            reAttemptCount += 1
        else:      
            reAttemptFlag = False      
            paper_id = search_result.get('paperId',"")
            print("paper_id:", paper_id)

    if reAttemptFlag or paper_id == "": #this DOI does not exist in semantic scholar so we can't pull any recommendations
        return recommended_publications

    reAttemptFlag = True
    reAttemptCount = 0
    while(reAttemptFlag and reAttemptCount < 10):    
        # now pull recommendations with this paper id
        search_result = data_retriever.retrieve_data(source=source, 
                                                        base_url=app.config['DATA_SOURCES'][source].get('recommendations-endpoint', ''),
                                                        search_term=paper_id+"?fields=title,publicationDate,externalIds&limit=10", 
                                                        failed_sources=[] )#pass empty list

        if type(search_result) != dict:
            reAttemptFlag = True
            print('Try again for recommendations')            
            time.sleep(2) #force one second delay between two consecutive requests
            reAttemptCount += 1
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

@utils.handle_exceptions
def get_citations_for_publication(source: str, doi: str):
     
    citations_list = []

    reAttemptFlag = True
    reAttemptCount = 0
    while(reAttemptFlag and reAttemptCount < 10):         
        search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('citations-endpoint', ''),
                                                    identifier=doi+"?fields=citations.title,citations.year,citations.externalIds,citations.authors")
        
        if type(search_result) != dict:    # and int(search_result) == 429:
            reAttemptFlag = True
            print('Try again for citations')            
            time.sleep(2) #force one second delay between two consecutive requests        
            reAttemptCount += 1
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
                _source.name = source
                publication.source.append(_source)
                
                citations_list.append(publication)   
    
    return citations_list 