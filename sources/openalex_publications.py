import requests
from objects import thing, Article, Author
import logging
import utils
from sources import data_retriever

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

        # base_url = utils.config["search_url_openalex_publications"]
        # url = base_url + search_term

        # headers = {'Accept': 'application/json',
        #            'Content-Type': 'application/json',
        #            'User-Agent': utils.config["request_header_user_agent"]
        #            }
        # response = requests.get(url, headers=headers, timeout=int(utils.config["request_timeout"]))        

        # logger.debug(f'OPENALEX PUBL response status code: {response.status_code}')
        # logger.debug(f'OPENALEX PUBL response headers: {response.headers}')

        # if response.status_code == 200:

        #     search_result = response.json()

        #     #clean the json response; remove all the keys which don't have any value
        #     search_result = utils.clean_json(search_result)

        
        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=utils.config["search_url_openalex_publications"],
                                                     search_term=search_term,
                                                     results=results)
        total_hits = search_result['meta']['count']
        logger.info(f'{source} - {total_hits} hits found')           

        if int(total_hits) > 0:
            hits = search_result['results']     
            for hit in hits:
                    
                    publication = Article()   

                    publication.name = hit.get("title", "")     
                    # print(publication.name)        
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