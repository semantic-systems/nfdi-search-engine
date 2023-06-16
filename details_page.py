import logging
import requests
import xml.etree.ElementTree as ET

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
# logger = logging.getLogger('nfdi_search_engine')


def search_openalex(search_term: str):
    details = {}
    links = []
    api_url = 'https://api.openalex.org/'
    if search_term.startswith('https://orcid.org/'):
        api_url += 'authors/'
    api_url_author = requests.get(api_url + search_term)
    if api_url_author.status_code != 404:
        author = api_url_author.json()
        links.append(author['id'])
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
    if search_term.startswith('https://orcid.org/'):
        url = 'https://dblp.org/orcid/' + search_term
    else:
        url = search_term
    headers = {'Accept': 'application/json'}
    response = requests.get(
        url + '.xml',
        headers=headers
    ).content

    details = {}
    links = []

    author = ET.fromstring(response)[0]
    name = author.find('.author').text
    links.append("https://dblp.uni-trier.de/pid/" + author.find('.author').attrib['pid'])
    if author.find('.note') is not None:
        details['Last known institution'] = author.find('.note').text
    for url in author.findall('.url'):
        links.append(url.text)
    return details, links, name

def get_orcid(search_term):
    if search_term.startswith('https://openalex.org/'):
        api_url = 'https://api.openalex.org/'
        api_url_author = requests.get(api_url + search_term)
        if api_url_author.status_code != 404:
            author = api_url_author.json()
            if author['orcid']:
                return author['orcid']
    if search_term.startswith('https://dblp'):
        headers = {'Accept': 'application/json'}
        response = requests.get(
            search_term + '.xml',
            headers=headers
        ).content
        author = ET.fromstring(response)[0]
        for url in author.findall('.url'):
            if url.text.startswith('https://orcid.org/'):
                return url.text
    return ''


def search_by_orcid(search_term):
    details_dblp, links_dblp, name = search_dblp(search_term)
    details_alex, links_alex, name = search_openalex(search_term)
    details_alex.update(details_dblp)
    links = list(dict.fromkeys(links_alex + links_dblp))
    return details_alex, links, name
