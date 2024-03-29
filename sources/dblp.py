import extruct
import requests
from objects import Person, Article
import logging
import os
import pprint
import utils
# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


def extract_metadata(text: bytes) -> object:
    """Extract all metadata present in the page and return a dictionary of metadata lists.

    Args:
        text: The content of a requests.get( ) call

    Returns:
        metadata (dict): Dictionary of json-ld, microdata, and opengraph lists.
        Each of the lists present within the dictionary contains multiple dictionaries.
    """
    metadata = extruct.extract(text,
                               uniform=True,
                               syntaxes=['json-ld',
                                         'microdata',
                                         'opengraph'])
    assert isinstance(metadata, object)
    return metadata


@utils.timeit
# def dblp(search_term: str, g, results):
def search(search_term: str, results):

    try:

        base_url = utils.config["search_url_dblp"]
        url = base_url + search_term

        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'User-Agent': utils.config["request_header_user_agent"]
                   }
        response = requests.get(url, headers=headers, timeout=int(utils.config["request_timeout"]))        

        logger.debug(f'DBLP response status code: {response.status_code}')
        logger.debug(f'DBLP response headers: {response.headers}')

        # TODO unclear why here are only a few but now all results returned

        metadata = extract_metadata(response.content)
        # TODO unclear why this loop takes so long
        #The profiler indicates that the JSON-LD parsing process is responsible for the majority of the execution time, taking approximately 18.21 seconds.
        #
        # I.e. the JSON-LD parsing takes that long
        for data in metadata['microdata']:
            if data['@type'] == 'Person':
                '''
                results.append(
                    Person(
                        name=data["name"],
                        url=data["url"],
                        affiliation=""
                    )
                )
                '''
            elif data['@type'] == 'ScholarlyArticle':
                if 'author' in data:
                    url = ''
                    if 'url' in data:
                        if type(data["url"]) == list:
                            url = ', '.join(data["url"])
                        else:
                            url = data["url"]
                    publication = Article()
                    publication.source = 'DBLP'
                    publication.name = data["name"]
                    publication.url = url
                    publication.image = data["image"]
                    publication.description = ''
                    publication.abstract = ''
                    publication.keywords.append('')
                    publication.inLanguage.append("")
                    publication.datePublished = data["datePublished"]
                    publication.license = ''
                    author = Person()
                    author.type = 'Person'
                    if type(data["author"]) == list:
                        #author = ', '.join([authors["name"] for authors in data["author"]])
                        for authors in data["author"]:
                            author2 = Person()
                            author2.name = authors["name"]
                            author2.type = 'Person'
                            publication.author.append(author2)
                    elif type(data["author"]) == dict:
                        author.name = data["author"]["name"]
                        publication.author.append(author)
                    else:
                        author.name = data["author"]
                        publication.author.append(author)
                    publication.encoding_contentUrl = ''
                    publication.encodingFormat = ''

                    results['publications'].append(publication)
                    '''
                    results.append(
                        Article(
                            title=data["name"],
                            url=url,
                            authors=author,
                            description='',
                            date=data["datePublished"]
                        )
                    )
                    '''
        logger.info(f"Got {len(results)} Researchers and scholarly articls from DBLP")
        # return results
        # g.parse(data=json.dumps(data), format='json-ld')
        # logger.info(f"Graph g has {len(g)} statements after querying DBLP.")
    
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('DBLP')
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')