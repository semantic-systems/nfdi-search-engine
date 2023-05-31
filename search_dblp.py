import extruct
import requests
from objects import Person, Article
import logging
import os

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


# def dblp(search_term: str, g, results):
def dblp(search_term: str, results):
    headers = {'Accept': 'application/json'}
    response = requests.get(
        'https://dblp.uni-trier.de/search?q=' + search_term,
        headers=headers
    )

    logger.debug(f'DBLP response status code: {response.status_code}')
    logger.debug(f'DBLP response headers: {response.headers}')

    # TODO unclear why here are only a few but now all results returned

    metadata = extract_metadata(response.content)

    # TODO unclear why this loop takes so long
    # The profiler indicates that the JSON-LD parsing process is responsible for the majority of the execution time, taking approximately 18.21 seconds.

    for data in metadata['microdata']:
        if data['@type'] == 'Person':
            results.append(
                Person(
                    name=data["name"],
                    url=data["url"],
                    affiliation=""
                )
            )
        elif data['@type'] == 'ScholarlyArticle':
            if 'author' in data:
                if type(data["author"]) == list:
                    author = ', '.join([authors["name"] for authors in data["author"]])
                elif type(data["author"]) == dict:
                    author = data["author"]["name"]
                else:
                    author = data["author"]
                url = ''
                if 'url' in data:
                    if type(data["url"]) == list:
                        url = ', '.join(data["url"])
                    else:
                        url = data["url"]
                results.append(
                    Article(
                        title=data["name"],
                        url=url,
                        authors=author,
                        description='',
                        date=data["datePublished"]
                    )
                )
    logger.info(f"Got {len(results)} Researchers and scholarly articls from DBLP")

