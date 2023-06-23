import logging
import threading
from string import Template

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
    if api_url_author.status_code != 200:
        return details, links, ''
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
    if not ET.fromstring(response):
        return details, links, ''
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
    elif search_term.startswith('https://dblp'):
        headers = {'Accept': 'application/json'}
        response = requests.get(
            search_term + '.xml',
            headers=headers
        ).content
        author = ET.fromstring(response)[0]
        for url in author.findall('.url'):
            if url.text.startswith('https://orcid.org/'):
                return url.text
    elif search_term.startswith('http://www.wikidata'):
        url = search_term
        headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
        response = requests.get(url, headers=headers)

        wikidata_id = search_term.split('/')[-1]

        if response.status_code == 200:
            data = response.json()
            author = (data['entities'][wikidata_id])
            if 'P496' in author['claims'].keys():
                orcid = author['claims']['P496'][0]['mainsnak']['datavalue']['value']
                return 'https://orcid.org/' + orcid
    return ''


def search_by_orcid(search_term):
    details_wiki, links_wiki, name = search_wikidata(search_term)
    details_dblp, links_dblp, name = search_dblp(search_term)
    details_alex, links_alex, name = search_openalex(search_term)
    details_wiki.update(details_alex)
    details_wiki.update(details_dblp)
    links = list(dict.fromkeys(links_alex + links_dblp + links_wiki))
    return details_wiki, links, name


def search_wikidata(search_term):
    details = {}
    links = []
    name = ''
    if search_term.startswith('http://www.wikidata'):
        url = search_term
        headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
        response = requests.get(url, headers=headers)

        wikidata_id = search_term.split('/')[-1]

        if response.status_code != 200:
            return details, links, name
        data = response.json()
        author = (data['entities'][wikidata_id])
        name = author.get('labels').get('en').get('value')
        if 'en' in author.get('descriptions').keys():
            details['Description'] = author.get('descriptions').get('en').get('value')
        links.append('https://www.wikidata.org/entity/' + wikidata_id)
        links_dict = author['claims']
        links += get_wiki_links(links_dict)
        return details, links, name

    elif search_term.startswith('https://orcid.org/'):
        orcid = search_term.split('/')[-1]
        url = 'https://query.wikidata.org/sparql'
        headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
        query_template = Template('''
        SELECT DISTINCT ?item ?itemLabel WHERE {
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
          {
            SELECT DISTINCT ?item WHERE {
              ?item p:P496 ?statement0.
              ?statement0 (ps:P496) "$orcid".
            }
            LIMIT 100
          }
        }
          ''')
        response = requests.get(url,
                                params={'format': 'json',
                                        'query': query_template.substitute(orcid=orcid),
                                        }, timeout=(3, 15), headers=headers)
        if response.status_code != 200:
            return details, links, name
        data = response.json()
        wikidata_link = ''
        match = data['results']['bindings']
        if match:
            wikidata_link = match[0]['item']['value']
            return search_wikidata(wikidata_link)
    return details, links, name

def get_wiki_links(links_dict):
    links = []
    headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
    for prop_code in links_dict.keys():
        url = 'https://www.wikidata.org/wiki/Special:EntityData/' + prop_code
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            continue
        data = response.json()
        claims = data['entities'][prop_code]['claims']
        end_of_link = links_dict[prop_code][0]['mainsnak']['datavalue']['value']
        if 'P1630' in claims.keys() and isinstance(end_of_link, str):
            formatter_link = claims['P1630'][0]['mainsnak']['datavalue']['value']
            links.append(formatter_link.replace('$1', end_of_link))
    return links
