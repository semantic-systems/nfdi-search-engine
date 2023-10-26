import requests
import logging
import utils

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

def retrieve_data(source: str, base_url: str, search_term: str, results):
    
    try:
        url = base_url + search_term

        headers = {'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': utils.config["request_header_user_agent"]
                    }
        response = requests.get(url, headers=headers, timeout=int(utils.config["request_timeout"]))        

        logger.debug(f'{source} response status code: {response.status_code}')
        logger.debug(f'{source} response headers: {response.headers}')

        if response.status_code == 200:

            search_result = response.json()

            #clean the json response; remove all the keys which don't have any value
            search_result = utils.clean_json(search_result)

            return search_result 

        else:
            logger.error(f'Response status code: {str(response.status_code)}')
            results['timedout_sources'].append(source)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('OPENALEX - Publications')
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')