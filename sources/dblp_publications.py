import requests
from objects import thing, Article, Author
import logging
import utils
from sources import data_retriever

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):

    source = "DBLP Publications"

    try:

        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=utils.config["search_url_dblp_publications"],
                                                     search_term=search_term,
                                                     results=results)

        # base_url = utils.config["search_url_dblp_publications"]
        # url = base_url + search_term

        # headers = {'Accept': 'application/json',
        #            'Content-Type': 'application/json',
        #            'User-Agent': utils.config["request_header_user_agent"]
        #            }
        # response = requests.get(url, headers=headers, timeout=int(utils.config["request_timeout"]))        

        # logger.debug(f'DBLP PUBL response status code: {response.status_code}')
        # logger.debug(f'DBLP PUBL response headers: {response.headers}')

        # if response.status_code == 200:

        #     search_result = response.json()

        hits = search_result['result']['hits']
        total_hits = hits['@total']

        logger.info(f'{source} - {total_hits} hits found')  

        if int(total_hits) > 0:
            hits = hits['hit']         

            for hit in hits:
                    
                    publication = Article()   

                    info = hit['info']
                    publication.name = info.get("title", "")             
                    publication.url = info.get("url", "")
                    publication.identifier = info.get("doi", "")
                    publication.datePublished = info.get("year", "") 
                    publication.license = info.get("access", "")
                    publication.publication = info.get("venue", "") 

                    authors = info.get("authors", {}).get("author", [])                        
                    for author in authors:
                        _author = Author()
                        _author.type = 'Person'
                        _author.name = author.get("text", "")
                        _author.identifier = author.get("@pid", "") #ideally this pid should be stored somewhere else
                        publication.author.append(_author)    

                    _source = thing()
                    _source.name = 'DBLP'
                    _source.identifier = hit.get("@id", "")
                    _source.url = info.get("url", "")                         
                    publication.source.append(_source)

                    results['publications'].append(publication)  
    
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')