import requests
import logging
import utils
from objects import thing, Article, Author
from sources import data_retriever
from datetime import datetime
from dateutil import parser
import traceback

logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term, results):

    source = "IEEE"

    try:

        # API key
        api_key = '4nm2vdr778weget78v9ubgdb'
        base_url = utils.config["search_url_ieee"]
        base_url = base_url.replace('{api_key}', api_key)

        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=base_url,
                                                     search_term=search_term,
                                                     results=results)
        
    #     # API key and 
    #     api_key = '4nm2vdr778weget78v9ubgdb'   

        # # search URL with the provided search term, API key, and max records
        # search_url = f'http://ieeexploreapi.ieee.org/api/v1/search/articles?querytext={search_term}&apikey={api_key}&max_records={max_records}'

        total_records = search_result.get("total_records", "")
        hits = search_result['articles']
        total_hits = len(hits)     

        logger.info(f'{source} - {total_records} records matched; pulled top {total_hits}') 

        if int(total_hits) > 0:
            for hit in hits:
                    
                publication = Article()   

                publication.name = hit.get("title", "")             
                publication.url = hit.get("html_url", "")
                publication.identifier = hit.get("doi", "")
                publication.datePublished = datetime.strftime(parser.parse(hit.get("insert_date", "")), '%Y-%m-%d') 
                publication.license = hit.get("access_type", "")
                publication.publication = hit.get('publisher', '')
                publication.description = utils.remove_html_tags(hit.get('abstract', ''))
                publication.abstract = publication.description
                publication.encoding_contentUrl= hit.get('pdf_url', '')

                authors = hit.get("authors", {}).get("authors", [])                        
                for author in authors:
                    _author = Author()
                    _author.type = 'Person'
                    _author.name = author.get("full_name", "")
                    _author.identifier = author.get("id", "") # ieee id of the author
                    publication.author.append(_author)    

                _source = thing()
                _source.name = source
                _source.identifier = hit.get("article_number", "")
                _source.url = hit.get("html_url", "")                         
                publication.source.append(_source)               

                results['publications'].append(publication)         

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())
        
    