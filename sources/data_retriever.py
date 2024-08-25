import requests
import logging
import utils
import urllib.parse
from main import app
from flask import request, flash

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

def retrieve_data(source: str, base_url: str, search_term: str, failed_sources):
    
    try:

        search_term = urllib.parse.quote_plus(string=search_term, safe='()?&=,')
        url = base_url + search_term
        # encode the url
        # url = urllib.parse.quote_plus(string=url, safe=';/?:@&=+$,')
        # url = urllib.parse.quote_plus(string=url)

        headers = {'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': app.config['REQUEST_HEADER_USER_AGENT'],     #utils.config["request_header_user_agent"]
                    }
        response = requests.get(url, headers=headers, timeout=int(app.config["REQUEST_TIMEOUT"]))        

        # logger.debug(f'{source} response status code: {response.status_code}')
        # logger.debug(f'{source} response headers: {response.headers}')

        if response.status_code == 200:
            search_result = response.json()
            #clean the json response; remove all the keys which don't have any value
            search_result = utils.clean_json(search_result)
            return search_result 
        else:
            failed_sources.append(source)
            utils.log_event(type="error", message=f"{source} - Response status code: {str(response.status_code)}")            
            return None
    
    except requests.exceptions.Timeout as ex:
        failed_sources.append(source)
        utils.log_event(type="error", message=f"{source} - timed out.")
        raise ex
    
    except Exception as ex:
        raise ex

def retrieve_single_object(source: str, base_url: str, doi: str):
    
    try:        
        doi = urllib.parse.quote_plus(string=doi, safe='()?&=,')
        url = base_url + doi
        # print('url:', url)
        headers = {'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': app.config['REQUEST_HEADER_USER_AGENT'], 
                    }
        response = requests.get(url, headers=headers, timeout=int(app.config["REQUEST_TIMEOUT"]))        

        # logger.debug(f'{source} response status code: {response.status_code}')
        # logger.debug(f'{source} response headers: {response.headers}')

        if response.status_code == 200:
            search_result = response.json()
            #clean the json response; remove all the keys which don't have any value
            search_result = utils.clean_json(search_result)
            return search_result 
        else:
            utils.log_event(type="error", message=f"{source} - Response status code: {str(response.status_code)}")     
            return None
        
    except requests.exceptions.Timeout as ex:
        # flash(f'{source} timed out.', 'danger')
        utils.log_event(type="error", message=f"{source} - timed out.")
        raise ex

    except Exception as ex:
        raise ex
