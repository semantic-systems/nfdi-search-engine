import logging
import requests
import xml.etree.ElementTree as ET

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
# logger = logging.getLogger('nfdi_search_engine')


def search_openalex(search_term: str):
    details = {}
    links = [search_term]
    api_url = "https://api.openalex.org/"
    api_url_author = requests.get(api_url + search_term)
    if api_url_author.status_code != 404:
        author = api_url_author.json()
        if author['orcid']:
            links.append(author['orcid'])
        if 'wikipedia' in author['ids'].keys():
            links.append(author['wikipedia'])
        if 'twitter' in author['ids'].keys():
            links.append(author['twitter'])
        if author['last_known_institution']:
            inst = author['last_known_institution']
            details['Last known institution'] = inst['display_name'] + ' (' + inst['country_code'] + ')'
        details['Number of works'] = author['works_count']
        details['Number of citations'] = author['cited_by_count']
        return details, links, author['display_name']
    return details, links, ''


def search_dblp(search_term: str):
    headers = {'Accept': 'application/json'}
    response = requests.get(
        search_term + '.xml',
        headers=headers
    ).content

    details = {}
    links = [search_term]

    author = ET.fromstring(response)[0]
    name = author.find('.author').text
    if author.find('.note') is None:
        details['Last known institution'] = ""
    else:
        details['Last known institution'] = author.find('.note').text
    for url in author.findall('.url'):
        links.append(url.text)
    return details, links, name
