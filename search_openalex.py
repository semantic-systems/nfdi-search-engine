import requests
import logging
from objects import Person, Article
import utils, json


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


# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


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
    logger.info(f'Got {len(results)} author records from OpenAlex')


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
    logger.info(f'Got {len(results)} publication records from OpenAlex')

