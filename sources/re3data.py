import time
from typing import List, Dict

import utils
from objects import Dataset, Organization
from main import app
from sources import data_retriever
from objects import thing


@utils.handle_exceptions
def search(source: str, search_term: str, results: Dict, failed_sources: List):
    start_time = time.time()  # TODO: Retrieval takes way too long!
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

    counter_repository_short_models = 0
    for repo in repositories:
        repository = Dataset(
            name=repo.get('name', ''),
            identifier=repo.get('doi', '').partition('doi.org/')[2],
            url=repo.get('doi', ''),
            source=[thing(name=source, url=repo.get('doi', ''))],
        )
        results['resources'].append(repository)
        counter_repository_short_models += 1

    utils.log_event(type="info",
                    message=f"{source} - retrieved {counter_repository_short_models} repository short models")
    print(f"searching Re3Data overview took {time.time() - start_time:.2f} seconds to execute")


    # counter_retrieved_resources = 0
    # for repo in repositories:
    #     details = data_retriever.retrieve_data(
    #         source=source,
    #         base_url=app.config['DATA_SOURCES'][source].get('details-endpoint', ''),
    #         search_term=repo['id'],
    #         failed_sources=failed_sources
    #     )
    #
    #     if details:
    #         creative_work = map_repository_to_creative_work(source, repo['doi'], details)
    #         results['resources'].append(creative_work)
    #         counter_retrieved_resources += 1
    #
    # utils.log_event(type="info", message=f"{source} - retrieved {counter_retrieved_resources} repository details")
    # print(f"searching Re3Data took {time.time() - start_time:.2f} seconds to execute")


def map_repository_to_creative_work(source: str, doi: str, repository_details: dict) -> Dataset:
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
            source=[thing(name=source, url=doi)],
        ) for inst in institutions
    ]

    # TODO: Why is only one funder allowed? -- Make a list! Look in other sources!!!
    funder = [org for org in organizations if 'funding' in org.keywords]

    languages = repository_data.get('r3d:repositoryLanguage', [])
    if isinstance(languages, str):
        languages = [languages]

    # ToDo: why was licenses not used in prev implementation? we use!
    license_names = repository_data.get('r3d:dataLicense', {})
    if isinstance(license_names, dict):
        license_names = [license_names.get('r3d:dataLicenseName', '')]
    else:
        license_names = [item.get('r3d:dataLicenseName', '') for item in license_names]

    # ToDo - does ContentType match the field logic of additionalType? Could it be a list also?
    content_types = repository_data.get('r3d:contentType', [])
    if isinstance(content_types, dict):
        content_types = [content_types.get('#text', '')]
    else:
        content_types = [ct.get('#text', '') for ct in content_types]

    # Todo: is this the correct way to use the genre field?  - list of subjects!
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
        identifier=doi.partition('doi.org/')[2],
        additionalType=', '.join(content_types),
        source=[thing(name=source, url=doi)], # ToDo: why is source not displayed on results page?  -> needs to be a thing()
        author=organizations,  # TODO: why are organizations as authors not displayed on the results overview page?
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

# ToDo: What about the details page, is it not implemented for the resources tab? Could we just open the doi link?
