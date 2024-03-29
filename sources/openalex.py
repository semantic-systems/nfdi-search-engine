import requests
import logging
from objects import Person, Author, Article, Institute, Funder, Publisher
import utils

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_key: str, results):    
    find_works(search_key, results)
    find_authors(search_key, results)
    # find_institute(search_key, results)
    # find_funder(search_key, results)
    # find_publisher(search_key, results)
    logger.info(f"Got {len(results)} author, publication, and institute records from OpenAlex")
    return results


def find_authors(search_key, results):

    try:
        base_url = utils.config["search_url_openalex_authors"]
        headers = {'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'User-Agent': utils.config["request_header_user_agent"]
                    }    
        response = requests.get(base_url + search_key, headers=headers, timeout=int(utils.config["request_timeout"]))

        if response.status_code == 200:
            search_result = response.json()

            records_found = search_result['meta']['count']
            logger.info(f'OpenAlex Authors - {records_found} records found')

            authors = search_result.get('results', None)
            if authors:
                for author in authors:
                    authorObj = Author()
                    authorObj.source = 'OpenAlex'
                    authorObj.name = author.get('display_name', '')
                    authorObj.orcid = author.get('orcid', '')

                    last_known_institution = author.get('last_known_institution', {})
                    if last_known_institution:
                        authorObj.affiliation = author.get('last_known_institution', {}).get('display_name')
                    else:
                        authorObj.affiliation = ''                    
                    authorObj.works_count = author.get('works_count', '')
                    authorObj.cited_by_count = author.get('cited_by_count', '')

                    results['researchers'].append(authorObj)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('OPENALEX')
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')

def find_works(search_key, results):

    try:        
        api_url = "https://api.openalex.org/works?search="
        api_response = requests.get(api_url + search_key, timeout=int(utils.config["request_timeout"]))
        if api_response.status_code != 404:
            api_data = api_response.json()
            for work in api_data['results']:
                if 'id' in work:
                    if work["display_name"] is None \
                            or work["id"] is None \
                            or work["doi"] is None \
                            or work["publication_date"] is None:
                        continue
                    publication = Article()
                    publication.source = 'OpenAlex'
                    publication.name = utils.remove_html_tags(work["display_name"])
                    publication.url = work["doi"]
                    # publication.image = hit_source.get("image", "")
                    publication.description = ''
                    if not work["abstract_inverted_index"] is None:
                        publication.description = generate_string_from_keys(work["abstract_inverted_index"]) # Generate the string using keys from the dictionary
                    publication.abstract = ''
                    keywords = work["concepts"]
                    if keywords:
                        for keyword in keywords:
                            publication.keywords.append(keyword["display_name"])

                    publication.inLanguage.append(str(work["language"]))
                    publication.datePublished = str(work["publication_date"])
                    publication.license = ''
                    if not work["primary_location"]["license"] is None:
                        publication.license = work["primary_location"]["license"]

                    if len(work["authorships"]) == 1:
                        author = Person()
                        author.name = work["authorships"][0]["author"]["display_name"]
                        author.type = 'Person'
                        author.identifier = work["id"]
                        publication.author.append(author)
                    else:
                        # authorship = ', '.join(
                        #   current_author["author"]["display_name"] for current_author in work["authorships"])
                        for current_author in work["authorships"]:
                            author = Person()
                            author.name = current_author["author"]["display_name"]
                            author.type = 'Person'
                            author.identifier = current_author["author"]["orcid"]
                            publication.author.append(author)

                    publication.encoding_contentUrl = ''
                    publication.encodingFormat = ''

                    results['publications'].append(publication)
                    ''''
                    results.append(
                        Article(
                            title=work["display_name"],
                            url=work["id"],
                            authors=author,
                            description='',
                            date=str(work["publication_year"])
                        )
                    )
                    '''

        # logger.info(f'Got {len(results)} publication records from OpenAlex')

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('OPENALEX')
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        
def find_institute(search_key, results):
    institute_api_url = "https://api.openalex.org/institutions?search="
    api_response = requests.get(institute_api_url + search_key, timeout=int(utils.config["request_timeout"]))
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
    api_response = requests.get(funder_api_url + search_key, timeout=int(utils.config["request_timeout"]))
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
    api_response = requests.get(publisher_api_url + search_key, timeout=int(utils.config["request_timeout"]))
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


def generate_string_from_keys(dictionary):
    keys_list = list(dictionary.keys())
    keys_string = " ".join(keys_list)
    return keys_string
