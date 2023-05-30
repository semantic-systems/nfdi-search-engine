import logging
import requests

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
# logger = logging.getLogger('nfdi_search_engine')


def search_openalex(search_term: str):
    details = {'OpenAlex': search_term}
    api_url = "https://api.openalex.org/"
    api_url_author = requests.get(api_url + search_term)
    if api_url_author.status_code != 404:
        author = api_url_author.json()
        if author['orcid']:
            details['ORCID number'] = author['orcid']
        details['Number of works'] = author['works_count']
        details['Number of citations'] = author['cited_by_count']
        return details, author['display_name']
    return details, ''


def search_dblp(search_term: str):
    headers = {'Accept': 'application/json'}
    response = requests.get(
        search_term + '.xml',
        headers=headers
    ).content

    print(response)
