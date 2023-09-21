import requests
import logging
import json
import utils
from objects import Article, Person

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):
    try:

        raise requests.exceptions.Timeout('Just checking timed out exception')
                
        base_url = utils.config["search_url_resodate"]
        url = base_url + '"' + search_term.replace(' ', '+') + '"'
        
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'User-Agent': utils.config["request_header_user_agent"]
                   }

        response = requests.get(url, headers=headers, timeout=int(utils.config["request_timeout"]))

        if response.status_code == 200:
            search_result = response.json()

            total_hits = search_result['hits']['total']['value']

            logger.info(f'RESODATE - {total_hits} hits/records found')

            if total_hits > 0:
                hits = search_result['hits']['hits']                

                for hit in hits:
                    hit_source = hit.get('_source', None)
                    publication = Article()
                    publication.source = 'RESODATE'
                    publication.name = hit_source.get("name", "")             
                    publication.url = hit_source.get("id", "")
                    publication.image = hit_source.get("image", "")
                    publication.description = utils.remove_html_tags(hit_source.get("description", ""))
                    publication.abstract = utils.remove_html_tags( hit_source.get("description", ""))
                    keywords = hit_source.get("keywords", None)
                    if keywords:
                        for keyword in keywords:
                            publication.keywords.append(keyword)

                    languages = hit_source.get("inLanguage", None)
                    if languages:
                        for language in languages:
                            publication.inLanguage.append(language)
                    
                    publication.datePublished = hit_source.get("datePublished", "") 
                    publication.license = hit_source.get("license", {}).get("id", "")

                    for creator in hit_source.get("creator", []):
                        if creator['type'] == 'Person':
                            author = Person()
                            author.type = creator['type']
                            author.name = creator.get("name", "")
                            author.identifier = creator.get("id", "") 
                            publication.author.append(author)  

                    encodings = hit_source.get("encoding", None)
                    if encodings:
                        for encoding in encodings:
                            publication.encoding_contentUrl = encoding.get("contentUrl", "")
                            publication.encodingFormat = encoding.get("encodingFormat", "")
                    
                    results['publications'].append(publication)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('RESODATE')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
