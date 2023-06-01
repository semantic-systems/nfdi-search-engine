import requests
import logging
from objects import Person, Article, Institute, Funder, Publisher
import json
import utils


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
    find_institute(search_key, results)
    find_funder(search_key, results)
    find_publisher(search_key, results)
    logger.info(f"Got {len(results)} author, publication, and institute records from OpenAlex")
    return results


def find_authors(search_key, results):
    author_api_url = "https://api.openalex.org/authors?search="
    api_response_authors = requests.get(author_api_url + search_key)
    if api_response_authors.status_code != 404:
        authors = api_response_authors.json()
        if 'results' in authors:
            for author in authors['results']:
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
    # logger.info(f'Got {len(results)} author records from OpenAlex')


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
                        description='',
                        date=str(work["publication_year"])
                    )
                )
    # logger.info(f'Got {len(results)} publication records from OpenAlex')


def find_institute(search_key, results):
    institute_api_url = "https://api.openalex.org/institutions?search="
    api_response = requests.get(institute_api_url + search_key)
    if api_response.status_code != 404:
        api_data = api_response.json()
        for institute in api_data["results"]:
            if 'id' in institute:
                institute_acronym = ', '.join(
                    inst_acronym for inst_acronym in institute["display_name_acronyms"])

                description = ''
                if 'wikipedia' in institute["ids"]:
                    # institute_wikipedia_link = institute["ids"]["wikipedia"]
                    description = utils.read_wikipedia(institute["display_name"])

                institute_country = ''
                if 'country' in institute["geo"]:
                    institute_country = institute["geo"]["country"]
                results.append(
                    Institute(
                        id=institute["id"],
                        name=institute["display_name"],
                        country=institute_country,
                        institute_type=institute["type"],
                        acronyms_name=institute_acronym,
                        homepage_url=institute["homepage_url"],
                        description=description)
                )
    # logger.info(f'Got {len(results)} institute records from OpenAlex')


def find_funder(search_key, results):
    funder_api_url = "https://api.openalex.org/funders?search="
    api_response = requests.get(funder_api_url + search_key)
    if api_response.status_code == 404:
        return
    api_data = api_response.json()
    for funder in api_data["results"]:
        if 'id' in funder:
            results.append(
                Funder(
                    id=funder["id"],
                    name=funder["display_name"],
                    homepage_url=funder["homepage_url"],
                    country_code=funder["country_code"],
                    grants_count=funder["grants_count"],
                    works_count=funder["works_count"],
                    description=funder["description"])
            )


def find_publisher(search_key, results):
    publisher_api_url = "https://api.openalex.org/publishers?search="
    api_response = requests.get(publisher_api_url + search_key)
    if api_response.status_code == 404:
        return
    api_data = api_response.json()
    for publisher in api_data["results"]:
        country_codes = ', '.join(
                country_code for country_code in publisher["country_codes"])
        h_index = ''
        if 'h_index' in publisher["summary_stats"]:
            h_index = publisher["summary_stats"]["h_index"]
        if 'id' in publisher:
            results.append(
                Publisher(
                    id=publisher["id"],
                    name=publisher["display_name"],
                    country_codes=country_codes,
                    works_count=publisher["works_count"],
                    homepage_url=publisher['homepage_url'],
                    h_index=h_index,
                    description='')
            )

