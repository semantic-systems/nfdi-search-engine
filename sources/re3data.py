import time
from typing import List, Dict

import utils
from objects import CreativeWork, Organization
from main import app
from sources import data_retriever


@utils.handle_exceptions
def search(source: str, search_term: str, results: Dict, failed_sources: List):
    start_time = time.time()  # TODO: Retrieval takes way too long!
    search_results = data_retriever.retrieve_data(source=source,
                                                  base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                  search_term=search_term,
                                                  failed_sources=failed_sources)

    # Iterate through each repository and retrieve details using its ID
    counter_retrieved_resources = 0
    repositories = search_results['list']['repository']
    repositories = [repositories] if isinstance(repositories, dict) else repositories
    for repo in repositories:
        # Call another API to get repository details
        details = data_retriever.retrieve_data(source=source,
                                               base_url=app.config['DATA_SOURCES'][source].get('details-endpoint', ''),
                                               search_term=repo['id'],
                                               failed_sources=failed_sources)

        if details is not None:
            creative_work = map_repository_to_creative_work(source=source,
                                                            doi=repo['doi'],
                                                            repository_details=details,)
            results['resources'].append(creative_work)
            counter_retrieved_resources += 1

    utils.log_event(type="info", message=f"{source} - retrieved {counter_retrieved_resources} repository details")

    end_time = time.time()
    duration = end_time - start_time
    print(f"searching Re3Data took {duration:.2f} seconds to execute")


def map_repository_to_creative_work(source: str, doi: str, repository_details: dict) -> CreativeWork:
    repository_data = repository_details.get('r3d:re3data', {}).get('r3d:repository', {})

    # TODO: we could also return a list of organizations for the organizations tab, not just resources/repositories
    authors = []
    funder = Organization()
    institutions = repository_data.get('r3d:institution', [])
    organizations = []
    if isinstance(institutions, dict):
        institutions = [institutions]
    for institution in institutions:
        organization = Organization(
            name=institution.get('r3d:institutionName', {}).get('#text', ''),
            alternateName=get_alternate_names(institution.get('r3d:institutionAdditionalName', {})),
            additionalType=institution.get('r3d:institutionType', ''),
            url=institution.get('r3d:institutionURL', ''),
            identifier=institution.get('r3d:institutionIdentifier', ''),
            location=institution.get('r3d:institutionCountry', ''),
            email=institution.get('r3d:institutionContact', ''),
            keywords=institution.get('r3d:responsibilityType', []),
            source=source
        )
        if 'funding' in organization.keywords:
            # select the first funding organization as funder since only one funder is permitted
            funder = organization if funder.name == '' else funder  # TODO: Why is only one funder allowed?
        organizations.append(organization)
    authors.extend(organizations) # TODO: why are organizations as authors not displayed on the results overview page?


    # Handle languages (ISO-639-3)
    languages = []
    if 'r3d:repositoryLanguage' in repository_data:
        if type(repository_data['r3d:repositoryLanguage']) is list:
            languages.extend(repository_data['r3d:repositoryLanguage'])
        else:
            languages.append(repository_data['r3d:repositoryLanguage'])

    # Handle licenses # ToDo: why was licenses not used in prev implementation?
    license_names = repository_data.get('r3d:dataLicense', {})
    if isinstance(license_names, dict):
        license_names = [license_names.get('r3d:dataLicenseName', '')]
    elif isinstance(license_names, list):
        license_names = [item.get('r3d:dataLicenseName', '') for item in license_names]
    license_url = ', '.join(set(license_names))

    # ToDo - does ContentType match the field logic of additionalType? Could it be a list also?
    raw_content_types = repository_data.get('r3d:contentType', [])
    content_type_list = [raw_content_types.get('#text', '')] \
        if isinstance(raw_content_types, dict) else [ct.get('#text', '') for ct in raw_content_types]
    additional_type = ', '.join(content_type_list)

    # Todo: is this the correct way to use the genre field?
    subject_data = repository_data.get('r3d:subject', [])
    if isinstance(subject_data, list):
        genre_list = [subject.get('#text', '') for subject in subject_data]
        genre = ', '.join(genre_list)
    else:
        genre = subject_data.get('#text', '')

    return CreativeWork(
        name=repository_data.get('r3d:repositoryName', {}).get('#text', ''),
        alternateName=get_alternate_names(repository_data.get('r3d:additionalName', {})),
        description=repository_data.get('r3d:description', {}).get('#text', ''),
        url=repository_data.get('r3d:repositoryURL', ""),
        identifier=doi.partition('doi.org/')[2],
        additionalType=additional_type,
        source=source, # ToDo: why is source not displayed on results page?
        author=organizations,
        sourceOrganization=organizations[0] if organizations else None, # ToDo: why only one Organization allowed?
        funder=funder,
        inLanguage=languages,
        license=license_url,
        keywords=repository_data.get('r3d:keyword', []),
        dateCreated=repository_data.get('r3d:startDate', ""),
        datePublished=repository_data.get('r3d:entryDate', ""),
        dateModified=repository_data.get('r3d:lastUpdate', ""),
        abstract=repository_data.get('r3d:description', {}).get('#text', ''),
        genre=genre,
        text=repository_data.get('r3d:remarks', "")
    )

# helper function to retrieve alternateNames
def get_alternate_names(additional_names) -> List[str]:
    alternate_names = []
    if isinstance(additional_names, dict):
        alternate_names.append(additional_names.get('#text', ''))
    return alternate_names

# ToDo: What about the details page, is it not implemented for the resources tab? Could we just open the doi link?
