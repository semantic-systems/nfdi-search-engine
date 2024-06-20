import requests
from objects import thing, Article, Author, Organization
import logging
import utils
from sources import data_retriever
import traceback

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):

    source = "DBLP Researchers"

    try:

        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=utils.config["search_url_dblp_researchers"],
                                                     search_term=search_term,
                                                     results=results)        

        hits = search_result['result']['hits']

        total_records_found = hits['@total']
        total_hits = hits['@sent']

        logger.info(f'{source} - {total_records_found} records matched; pulled top {total_hits}')  

        if int(total_hits) > 0:
            hits = hits['hit']         
            index = 0
            for hit in hits:
                    
                author = Author()
                info = hit.get('info',{})

                author.name = info.get('author', '')
                alias = info.get('aliases', {}).get('alias', '')
                if isinstance(alias, str):
                    author.alternateName.append(alias)
                if isinstance(alias, list):
                    for _alias in alias:
                        author.alternateName.append(_alias)

                affiliations = info.get('notes', {}).get('note', {})
                if isinstance(affiliations, list):
                    for affiliation in affiliations:
                        if affiliation.get('@type', '') == 'affiliation':
                            _organization = Organization()
                            _organization.name = affiliation.get('text', '')
                            author.affiliation.append(_organization)
                if isinstance(affiliations, dict):
                    if affiliations.get('@type', '') == 'affiliation':
                        _organization = Organization()
                        _organization.name = affiliations.get('text', '')
                        author.affiliation.append(_organization)
                                            
                # author.works_count = ''
                # author.cited_by_count = ''

                _source = thing()
                _source.name = 'DBLP'
                _source.identifier = hit.get("@id", "")
                _source.url = info.get("url", "")                         
                author.source.append(_source)

                author.list_index = f'dblp{index}'
                index += 1
                results['researchers'].append(author)                

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())