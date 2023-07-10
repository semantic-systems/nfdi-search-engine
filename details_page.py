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
    if author.find('.note') is not None:
        details['Last known institution'] = author.find('.note').text
    for url in author.findall('.url'):
        links.append(url.text)
    return details, links, name


def search_wikidata(search_term: str):
    formatter_urls = {'P214': 'https://viaf.org/viaf/$1/', 'P227': 'https://d-nb.info/gnd/$1',
                      'P2456': 'https://dblp.org/search/author/api?q=$1',
                      'P1960': 'https://scholar.google.com/citations?user=$1',
                      'P496': 'https://orcid.org/$1', 'P10897': 'https://orkg.org/resource/$1',
                      'P1153': 'https://www.scopus.com/authid/detail.uri?authorId=$1',
                      'P2002': 'https://twitter.com/$1'}
    details = {}
    links = []
    name = ''
    url = search_term
    headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return details, links, name

    wikidata_id = search_term.split('/')[-1]
    data = response.json()
    author = data['entities'][wikidata_id]
    name = author.get('labels').get('en').get('value')
    if 'en' in author.get('descriptions').keys():
        details['Description'] = author.get('descriptions').get('en').get('value')
    links.append('https://www.wikidata.org/entity/' + wikidata_id)
    links_dict = author['claims']
    for code in links_dict.keys():
        end_of_link = links_dict[code][0]['mainsnak']['datavalue']['value']
        if code in formatter_urls:
            link = formatter_urls[code].replace('$1', end_of_link)
            links.append(link)
        else:
            link = get_wiki_link(code)
            if link is not None and isinstance(end_of_link, str):
                links.append(link.replace('$1', end_of_link))
    return details, links, name

def get_wiki_link(code):
    headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
    url = 'https://www.wikidata.org/wiki/Special:EntityData/' + code
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return
    data = response.json()
    claims = data['entities'][code]['claims']
    if 'P1630' in claims.keys():
        formatter_link = claims['P1630'][0]['mainsnak']['datavalue']['value']
        return formatter_link
    return
