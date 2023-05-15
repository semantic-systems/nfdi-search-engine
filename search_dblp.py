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
    # PW:
    # The profiler says:
    #          3188239 function calls (3012651 primitive calls) in 18.210 seconds
    #
    #    Ordered by: cumulative time
    #
    #    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    #        30    0.000    0.000   18.210    0.607 graph.py:1223(parse)
    #        30    0.008    0.000   18.202    0.607 jsonld.py:81(parse)
    #        30    0.000    0.000   18.189    0.606 jsonld.py:118(to_rdf)
    #        30    0.019    0.001   18.189    0.606 jsonld.py:146(parse)
    #        30    0.000    0.000   18.107    0.604 context.py:365(load)
    #     60/30    0.001    0.000   16.618    0.554 context.py:390(_prep_sources)
    #        30    0.001    0.000   16.615    0.554 context.py:430(_fetch_context)
    #        60    0.002    0.000   16.615    0.277 util.py:27(source_to_json)
    #        60    0.001    0.000   13.612    0.227 parser.py:332(create_input_source)
    #        30    0.000    0.000   13.611    0.454 parser.py:436(_create_input_source_from_location)
    #        30    0.003    0.000   13.608    0.454 parser.py:231(__init__)
    # ...
    #
    # I.e. the JSON-LD parsing takes that long
    for data in metadata['microdata']:
        if data['@type'] == 'Person':
            # E.g:
            # {
            #   '@type': 'Person',
            #   '@context': 'http://schema.org',
            #   'additionalType': 'https://dblp.org/rdf/schema#Person',
            #   'url': 'https://dblp.uni-trier.de/pid/65/9656',
            #   'name': 'Ricardo Usbeck'
            # }
            results.append(
                Person(
                    name=data["name"],
                    url=data["url"],
                    affiliation=""
                )
            )
        elif data['@type'] == 'ScholarlyArticle':
            # E.g.
            # {
            #   '@type': 'ScholarlyArticle',
            #   '@context': 'http://schema.org',
            #   'additionalType': 'https://dblp.org/rdf/schema#Publication',
            #   'image': 'https://dblp.uni-trier.de/img/paper-oa.dark.hollow.16x16.png',
            #   'url': 'https://doi.org/10.1109/ACCESS.2022.3173355',
            #   'headline': 'Md. Rashad Al Hasan Rony, ...',
            #   'author':
            #     [
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/251/0778.html',
            #         'name': 'Md. Rashad Al Hasan Rony'
            #       },
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/213/7337.html',
            #         'name': 'Debanjan Chaudhuri'
            #       },
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/65/9656.html',
            #         'name': 'Ricardo Usbeck'
            #       },
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/71/4882.html',
            #         'name': 'Jens Lehmann'
            #       }
            #     ],
            #   'name': 'Tree-KGQA: An Unsupervised Approach for Question...',
            #   'isPartOf':
            #     [
            #       {
            #         '@type': 'Periodical',
            #         'name': 'IEEE Access'
            #       },
            #       {
            #         '@type': 'PublicationVolume',
            #         'volumeNumber': '10'
            #       }
            #     ],
            #   'pagination': '50467-50478',
            #   'datePublished': '2022'
            # }
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
                    date=data["datePublished"]
                )
            )
    logger.info(f"Got {len(results)} Researchers and scholarly articls from DBLP")
    # return results
    # g.parse(data=json.dumps(data), format='json-ld')
    # logger.info(f"Graph g has {len(g)} statements after querying DBLP.")
