import time
from typing import List, Dict

import utils
from objects import Dataset, Organization
from main import app
from sources import data_retriever
from objects import thing


@utils.handle_exceptions
def search(source: str, search_term: str, results: Dict, failed_sources: List):
    """
    Search for repositories in the Re3Data registry based on the search term. For re3data, the returned search results
    are only short models of repositories and do not contain detailed information, since very limited information
    is returned by the search-term-ready API and looping over all details is too time-consuming.
    The detailed information is retrieved separately for each (list of ) repository in search_displayed_resources().
    :param source: the source to search (re3data)
    :param search_term: the search term
    :param results: the dictionary to store the search results
    :param failed_sources: the list to store the failed

    :return: None
    """
    # start_time = time.time()
    search_url = app.config['DATA_SOURCES'][source].get('search-endpoint', '')
    search_results = data_retriever.retrieve_data(
        source=source,
        base_url=search_url,
        search_term=search_term,
        failed_sources=failed_sources
    )

    repositories = search_results['list'].get('repository', [])
    if isinstance(repositories, dict):
        repositories = [repositories]

    repositories_to_parse = repositories[:app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']]
    utils.log_event(type="info", message=f"{source} - {len(repositories)} records matched; pulled top {len(repositories_to_parse)}")   
    
    for repo in repositories_to_parse:
        repository = Dataset(
            name=repo.get('name', ''),
            identifier=repo.get('doi', '').partition('doi.org/')[2],
            url=repo.get('link', {}).get('@href', ''),
            source=[thing(name=source, url=repo.get('doi', ''), identifier=repo.get('link', {}).get('@href', '').partition('https://www.re3data.org/api/beta/repository/')[2])],
            partiallyLoaded=True,
        )
        results['resources'].append(repository)         

@utils.handle_exceptions
def search_displayed_resources(displayed_repos: List[Dataset], results: Dict, failed_sources: List):
    """
    Retrieve detailed information for each repository in the list of displayed repositories. Since a separate API call
    is needed for each repository, this function is time-consuming, and the number of repositories should be limited.

    :param displayed_repos: the list of repositories to retrieve detailed information for
    :param results: the dictionary to store the search results
    :param failed_sources: the list to store the failed

    :return: None
    """
    # start_time = time.time()
    source_name = displayed_repos[0].source[0].name if displayed_repos else "re3data"

    counter_retrieved_resources = 0
    for repo in displayed_repos:
        base_url = app.config['DATA_SOURCES'][source_name].get('details-endpoint', '')
        details = data_retriever.retrieve_data(
            source=source_name,
            base_url=base_url,
            search_term=repo.url.partition('https://www.re3data.org/api/beta/repository/')[2],
            failed_sources=failed_sources
        ) if repo.source else None

        if details:
            dataset = map_repository_to_dataset(source_name, repo.identifier, details)
            results['resources'].append(dataset)
            counter_retrieved_resources += 1

    utils.log_event(type="info", message=f"{source_name} - retrieved {counter_retrieved_resources} repository details")
    # print(f"searching Re3Data details took {time.time() - start_time:.2f} seconds to execute")

@utils.handle_exceptions
def get_resource(source: str, source_identifier: str, doi: str):
    """
    Retrieve detailed information for the repository. 

    :param source: source label for the data source; in this case its re3data
    :param source_identifier: the primay identifier in the source records
    :param doi: digital identifier for the resource

    :return: dataset
    """
    base_url = app.config['DATA_SOURCES'][source].get('get-resource-endpoint', '')     
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=base_url,
                                                    identifier=source_identifier) #source identifier will be passed on with the base url
    if search_result:
        dataset = map_repository_to_dataset(source, doi, search_result)
        utils.log_event(type="info", message=f"{source} - retrieved repository details")
        return dataset

def map_repository_to_dataset(source: str, doi: str, repository_details: dict) -> Dataset:
    """
    Map the detailed information of a repository to a Dataset object.

    :param source: the source of the information about the repository (re3data)
    :param doi: the DOI of the repository
    :param repository_details: the detailed information of the repository from the API

    :return: Dataset - repository in the form of a dataset object
    """
    repository_data = repository_details.get('r3d:re3data', {}).get('r3d:repository', {})

    institutions = repository_data.get('r3d:institution', [])
    if isinstance(institutions, dict):
        institutions = [institutions]

    organizations = [
        Organization(
            name=inst.get('r3d:institutionName', {}).get('#text', ''),
            alternateName=get_alternate_names(inst.get('r3d:institutionAdditionalName', {})),
            additionalType=inst.get('r3d:institutionType', ''),
            url=inst.get('r3d:institutionURL', ''),
            identifier=inst.get('r3d:institutionIdentifier', ''),
            location=inst.get('r3d:institutionCountry', ''),
            email=inst.get('r3d:institutionContact', ''),
            keywords=inst.get('r3d:responsibilityType', []),
            source=[thing(name=source,
                          url='https://www.re3data.org/repository/' +
                              repository_data.get('r3d:re3data.orgIdentifier', ""))]
        ) for inst in institutions
    ]

    funder = [org for org in organizations if 'funding' in org.keywords]

    languages = repository_data.get('r3d:repositoryLanguage', [])
    if isinstance(languages, str):
        languages = [languages]

    license_names = repository_data.get('r3d:dataLicense', {})
    if isinstance(license_names, dict):
        license_names = [license_names.get('r3d:dataLicenseName', '')]
    else:
        license_names = [item.get('r3d:dataLicenseName', '') for item in license_names]

    content_types = repository_data.get('r3d:contentType', [])
    if isinstance(content_types, dict):
        content_types = [content_types.get('#text', '')]
    else:
        content_types = [ct.get('#text', '') for ct in content_types]

    subjects = repository_data.get('r3d:subject', [])
    if isinstance(subjects, dict):
        subjects = [subjects.get('#text', '')]
    else:
        subjects = [subject.get('#text', '') for subject in subjects]

    return Dataset(
        name=repository_data.get('r3d:repositoryName', {}).get('#text', ''),
        alternateName=get_alternate_names(repository_data.get('r3d:additionalName', {})),
        description=repository_data.get('r3d:description', {}).get('#text', ''),
        url=repository_data.get('r3d:repositoryURL', ""),
        identifier=doi,
        additionalType=', '.join(content_types),
        source=[thing(name=source,
                      url='https://www.re3data.org/repository/' +
                          repository_data.get('r3d:re3data.orgIdentifier', ""))],
        author=organizations,
        sourceOrganization=organizations[0] if organizations else None,
        funder=funder,
        inLanguage=languages,
        license=', '.join(set(license_names)),
        keywords=repository_data.get('r3d:keyword', []),
        dateCreated=repository_data.get('r3d:startDate', ""),
        datePublished=repository_data.get('r3d:entryDate', ""),
        dateModified=repository_data.get('r3d:lastUpdate', ""),
        abstract=repository_data.get('r3d:description', {}).get('#text', ''),
        genre=subjects,
        text=repository_data.get('r3d:remarks', "")
    )

def get_alternate_names(additional_names) -> List[str]:
    if isinstance(additional_names, dict):
        return [additional_names.get('#text', '')]
    return []