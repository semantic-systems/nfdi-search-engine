import requests
import urllib.parse
from config import Config
import xmltodict

from nfdi_search_engine.common.formatting import clean_json


def retrieve_data(base_url: str, search_term: str, url: str = "", quote: bool = True):
    # Either the request will have base url and search then the url will be formed concatenating both of them
    # otherwise the url will be used as is.
    if url == "":
        if quote:
            # encode the search term
            search_term = urllib.parse.quote_plus(
                string=search_term,
                safe='()?&=,'
            )
        url = base_url + search_term

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': Config.REQUEST_HEADER_USER_AGENT,
    }

    response = requests.get(
        url, headers=headers, timeout=int(Config.REQUEST_TIMEOUT)
    )
    response.raise_for_status()

    if 'xml' in response.headers.get('content-type'):
        search_result = xmltodict.parse(response.text)
    else:
        search_result = response.json()

    # clean the json response; remove all the keys which don't have any value
    search_result = clean_json(search_result)
    return search_result


def retrieve_object(base_url: str, identifier: str, quote: bool = True):
    if quote:
        # encode the identifier
        identifier = urllib.parse.quote_plus(string=identifier, safe='()?&=,')
    url = base_url + identifier
    # print('url:', url)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': Config.REQUEST_HEADER_USER_AGENT,
    }
    response = requests.get(
        url, headers=headers, timeout=int(Config.REQUEST_TIMEOUT)
    )
    response.raise_for_status()

    if 'xml' in response.headers.get('content-type'):
        search_result = xmltodict.parse(response.text)
    else:
        search_result = response.json()

    # clean the json response; remove all the keys which don't have any value
    search_result = clean_json(search_result)

    return search_result
