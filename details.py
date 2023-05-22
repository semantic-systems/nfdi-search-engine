import os
import json
import utils
import extruct
import logging
import requests
from objects import Zenodo
from objects import Person, Article

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
detailslogger = logging.getLogger('nfdi_search_engine')


def extract_detailsdata(text: bytes) -> object:
    """Extract all metadata present in the page and return a dictionary of metadata lists.

    Args:
        text: The content of a requests.get( ) call

    Returns:
        metadata (dict): Dictionary of json-ld, microdata, and opengraph lists.
        Each of the lists present within the dictionary contains multiple dictionaries.
    """
    detailsdata = extruct.extract(text,
                               uniform=True,
                               syntaxes=['json-ld',
                                         'microdata',
                                         'opengraph'])
    assert isinstance(detailsdata, object)
    return detailsdata


# def dblp(search_term: str, g, results):
def dblp(search_term: str, results):
    headers = {'Accept': 'application/json'}
    response = requests.get(
        'https://dblp.uni-trier.de/search?q=' + search_term,
        headers=headers
    )

    detailslogger.debug(f'DBLP response status code: {response.status_code}')
    detailslogger.debug(f'DBLP response headers: {response.headers}')

    # TODO unclear why here are only a few but now all results returned

    detailsdata = extract_detailsdata(response.content)

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
    for data in detailsdata['microdata']:
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
    detailslogger.info(f"Got {len(results)} Researchers and scholarly articles from DBLP")
    # return results
    # g.parse(data=json.dumps(data), format='json-ld')
    # detailslogger.info(f"Graph g has {len(g)} statements after querying DBLP.")

def open_alex(name, g, results):
    """
    Obtain the results from the database request handles them accordingly
        Initially authored by Tilahun Taffa
    Args:
        name: keyword to search for
        g: graph containing the search answer
        results: search answer formatted into the data types of Person and Article

    Returns:
        the graph object and the results array

    """
    serializable_results, results = find(name, results)
    search_result = json.dumps(serializable_results)
    g.parse(data=search_result, format='json-ld')
    return g, results

def find(search_key: str, results):
    find_authors(search_key, results)
    find_works(search_key, results)
    return results


def find_authors(search_key, results):
    author_api_url = "https://api.openalex.org/authors?search="
    api_response_authors = requests.get(author_api_url + search_key)
    if api_response_authors.status_code != 404:
        authors = api_response_authors.json()
        if 'results' in authors:
            for author in authors['results']:
                # E.g.:
                #  {
                #    "id": "https://openalex.org/A4222267058",
                #    "orcid": None,
                #    "display_name": "Ricardo Usbeck",
                #    "display_name_alternatives": [],
                #    "relevance_score": 184.41525,
                #    "works_count": 1,
                #    "cited_by_count": 4,
                #    "ids": {
                #      "openalex": "https://openalex.org/A4222267058"
                #    },
                #    "x_concepts": [
                #      ...
                #    ],
                #    "counts_by_year": [
                #      {
                #        "year": 2022,
                #        "works_count": 1,
                #        "cited_by_count": 4
                #      }
                #    ],
                #    "works_api_url": "https://api.openalex.org/works?filter=author.id:A4222267058",
                #    "updated_date": "2023-01-18T18:01:48.538514",
                #    "created_date": "2022-04-05"
                # }
                if author['last_known_institution']:
                    affiliation = author['last_known_institution']['display_name']

                if author['display_name'] and author['id'] and author['last_known_institution']:
                    results.append(
                        Person(
                            name=author['display_name'],
                            url=author['id'],
                            affiliation=affiliation
                        )
                    )
    detailslogger.info(f'Got {len(results)} author records from OpenAlex')


def find_works(search_key, results):
    api_url = "https://api.openalex.org/works?search="
    api_response = requests.get(api_url + search_key)
    if api_response.status_code != 404:
        api_data = api_response.json()
        for work in api_data['results']:
            if 'id' in work:
                if work["display_name"] is None \
                        or work["id"] is None \
                        or work["publication_year"] is None:
                    continue

                if len(work["authorships"]) == 1:
                    author = work["authorships"][0]["author"]["display_name"]
                else:
                    author = ', '.join(
                        current_author["author"]["display_name"] for current_author in work["authorships"])
                results.append(
                    Article(
                        title=work["display_name"],
                        url=work["id"],
                        authors=author,
                        date=str(work["publication_year"])
                    )
                )
    detailslogger.info(f'Got {len(results)} publication records from OpenAlex')

def zenodo(search_term, results):
    response = requests.get('https://zenodo.org/api/records',
                            params={'q': search_term,
                                    'access_token': 'rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL'})

    detailslogger.debug(f'Zenodo response status code: {response.status_code}')
    detailslogger.debug(f'Zenodo response headers: {response.headers}')

    for data in response.json()['hits']['hits']:
        if 'conceptdoi' in data:
            # TODO Align and extend with schema.org concepts
            # resource = _make_zenodo_uri(data)
            # resource_type = URIRef('zenodo:' + data['detailsdata']['resource_type']['type'])
            resource_type = 'zenodo:' + data['detailsdata']['resource_type']['type']
            authors_list = '; '.join([authors["name"] for authors in data['detailsdata']['creators']])
            results.append(
                Zenodo(
                    resource_type=resource_type,
                    url=data["links"]["doi"],
                    date=data['detailsdata']['publication_date'],
                    title=data['detailsdata']['title'],
                    author=authors_list
                )
            )
    detailslogger.info(f'Got {len(results)} records from Zenodo')
    # return results
    # logger.info(f"Graph g has {len(g)} statements after querying Zenodo.")
