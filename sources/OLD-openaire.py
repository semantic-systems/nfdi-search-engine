import requests
import utils
from objects import Dataset, Author, Article, CreativeWork, Organization, Project
from main import app
import logging
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_string: str, results):
    """ Obtain the results from Openaire request and handles them accordingly.

          Args:
              search_string: keyword(s) to search for
              results: search answer formatted into different data types according to Openaire result_types
              and mapped to schema.org types.

          Returns:
                the results Object
          """
    openaire_product_search(search_string, results)
    openaire_project_search(search_string, results)

    logger.info(f"Got {len(results)} records from Openaire")
    return results


def openaire_product_search(search_string, results):

    try:
        api_url = 'https://api.openaire.eu/search/researchProducts'
        response = requests.get(api_url,
                                params={"keywords": search_string, "format": "json", "size": 20},
                                timeout=int(app.config["REQUEST_TIMEOUT"]))
        data = response.json()
        logger.debug(f'Openaire product search response status code: {response.status_code}')
        logger.debug(f'Openaire product search response headers: {response.headers}')

        # hits = data.get('response', {}).get('results', {}).get('result', [])
        if response.status_code == 200:
            try:
                hits = data.get('response', {}).get('results', {}).get('result', [])
            except AttributeError:
                hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

            for hit in hits:
                pro_result = hit.get('metadata', {}).get('oaf:entity', {}).get('oaf:result', {})
                result_type = pro_result.get('resulttype', {}).get('@classid', 'other')
                # check result type to create an Object of the right Class
                if result_type == 'publication':
                    product = Article()
                elif result_type == 'dataset':
                    product = Dataset()
                else:
                    product = CreativeWork()

                product.source = 'Openaire'
                collectedfrom = pro_result.get('collectedfrom', None)
                if collectedfrom:
                    product.originalSource = collectedfrom.get('@name', None)

                product.genre = result_type
                date = pro_result.get('dateofacceptance', None)
                if date:
                    product.datePublished = date['$']

                # title can be dict or list. If list, there are 'main title' and 'alternate title'
                if type(pro_result.get('title')) is dict:
                    product.name = pro_result.get('title', {}).get('$', '')
                elif type(pro_result.get('title')) is list:
                    for item in pro_result.get('title'):
                        if item['@classid'] == 'main title':
                            product.name = item['$']

                # description can be dict or list
                if type(pro_result.get('description')) is dict:
                    product.description = utils.remove_html_tags(pro_result.get('description', {}).get('$', ''))
                elif type(pro_result.get('description')) is list:
                    product.description = utils.remove_html_tags(pro_result.get('description')[0].get('$', ''))
                else:
                    product.description = ''

                # Language can be set or "und" = Undetermined
                product.inLanguage = [] if pro_result.get('language', {}).get('@classid', '') == 'und' else [pro_result.get(
                    'language', {}).get('@classid', '')]

                # pid can be dict or list
                if type(pro_result.get('pid')) is dict:
                    product.identifier = pro_result.get('pid', {}).get('$', '')
                elif type(pro_result.get('pid')) is list:
                    product.identifier = pro_result.get('pid', {})[0].get('$', '')
                else:
                    product.identifier = ''

                # Creators can be dict, list, None
                # creators = pro_result.get('creator', {}) if pro_result.get('creator') is not None else {}
                creators = pro_result.get('creator', None)
                if type(creators) is dict:
                    creator = Author()
                    creator.type = 'Person'
                    creator.name = creators.get('$', '')
                    product.author.append(creator)
                elif type(creators) is list:
                    for item in creators:
                        creator = Author()
                        creator.type = 'Person'
                        creator.name = item.get('$', '')
                        product.author.append(creator)

                # Check genre to add result to right category
                if product.genre == 'publication':
                    results['publications'].append(product)
                elif product.genre == 'dataset' or product.genre == 'software':
                    results['resources'].append(product)
                else:
                    results['others'].append(product)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('OPENAIRE')
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')

def openaire_project_search(search_string, results):

    try:
        api_url = 'https://api.openaire.eu/search/projects'
        response = requests.get(api_url, 
                                params={"name": search_string, "format": "json", "size": 20},
                                timeout=int(app.config["REQUEST_TIMEOUT"]))
        data = response.json()
        logger.debug(f'Openaire project search response status code: {response.status_code}')
        logger.debug(f'Openaire project search response headers: {response.headers}')

        if response.status_code == 200:
            try:
                hits = data.get('response', {}).get('results', {}).get('result', [])
            except AttributeError:
                hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

            for hit in hits:
                pro_result = hit.get('metadata', {}).get('oaf:entity', {}).get('oaf:project', {})
                project = Project()
                project.source = 'Openaire'
                project.name = pro_result.get('title', {}).get('$', '')
                project.dateStart = pro_result.get('startdate', {}).get('$', '')
                project.dateEnd = pro_result.get('enddate', {}).get('$', '')
                project.identifier = pro_result.get('callidentifier', {}).get('$', '')

                # fundingtree can be dict or list
                # fundingtree = pro_result.get('fundingtree', {}) if pro_result.get('fundingtree') is not None else {}
                fundingtree = pro_result.get('fundingtree', None)
                if type(fundingtree) is dict:
                    orga = Organization()
                    orga.name = fundingtree.get('name', {}).get('$', '')
                    project.funder.append(orga)
                elif type(fundingtree) is list:
                    for item in fundingtree:
                        orga = Organization()
                        orga.name = item.get('name', {}).get('$', '')
                        project.funder.append(orga)

                # "rels" can be None, dict, list
                relations = pro_result.get('rels', {}).get('rel', {}) if pro_result.get('rels', {}) is not None else []
                if type(relations) is dict:
                    relations = [relations]

                # This need a review. Type 'Organization' ?
                for rel in relations:
                    author_obj = Author()
                    author_obj.type = 'Organization'
                    author_obj.name = (rel.get('legalname', {}).get('$', ''))
                    project.author.append(author_obj)
                results['others'].append(project)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('OPENAIRE')
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')