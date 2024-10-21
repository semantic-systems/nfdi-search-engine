from elg.utils.errors import ensure_response_ok

from objects import thing, Dataset, SoftwareApplication, Organization, Project, CreativeWork
import utils
from elg import Catalog

import urllib
from typing import List, Dict

from sources import data_retriever


def set_common_attributes(obj, name, alternate_name, identifier, description, keywords, licences, in_language, country_of_origin, additional_type, version, date_published, date_modified):
    obj.name = name
    obj.alternateName = alternate_name
    obj.identifier = identifier
    obj.description = description
    obj.keywords = keywords
    obj.license = licences
    obj.inLanguage = in_language
    obj.countryOfOrigin = country_of_origin
    obj.additionalType = additional_type
    obj.version = version
    obj.datePublished = date_published
    obj.dateModified = date_modified
    return obj

@utils.handle_exceptions
def search(source: str, search_term: str, results: Dict, failed_sources: List):
    class CatalogDataRetriever(Catalog):
        def _get(self, path: str, queries: List[set] = None, json: bool = False):
            base_url = (
                "https://live.european-language-grid.eu/catalogue_backend/api/registry/"
                + path
                + ("?" if len(queries) >= 1 else "")
                + "&".join([f"{query}={urllib.parse.quote_plus(str(value))}" for (query, value) in queries])
            )
            response = data_retriever.retrieve_data(source=source,
                                                    base_url=base_url,
                                                    search_term='',
                                                    failed_sources=failed_sources,
                                                    clean_json=False,
                                                    elg=True)
            # check if response is a json object
            if isinstance(response, dict):
                return response
            ensure_response_ok(response)

    catalog = CatalogDataRetriever()
    elg_results = catalog.search(search=search_term, limit=100)

    counter_retrieved_resources = 0
    for result in elg_results:
        licences = ', '.join(set(result.licences))
        description = utils.remove_html_tags(result.description)
        name = result.resource_name
        date_published = str(result.creation_date)
        date_modified = str(result.last_date_updated)
        keywords = result.keywords if isinstance(result.keywords, list) else []
        in_language = result.languages if isinstance(result.languages, list) else []
        country_of_origin = result.country_of_registration
        additional_type = result.resource_type
        version = result.version if hasattr(result, 'version') else None
        alternate_name = result.resource_short_name
        identifier = str(result.id)

        if result.entity_type == 'Organization':
            organization = Organization()
            organization.name = name
            organization.alternateName = alternate_name
            organization.identifier = identifier
            organization.description = description
            organization.keywords = keywords
            organization.url = 'https://live.european-language-grid.eu/catalogue/organization/' + str(result.id)
            organization.source = [thing(name='ELG: Organization', url=organization.url)]
            organization.location = str(set(result.country_of_registration))
            results['organizations'].append(organization)
            counter_retrieved_resources += 1
            continue
        elif result.entity_type == 'Project':
            project = Project()
            project.url = 'https://live.european-language-grid.eu/catalogue/project/' + str(result.id)
            project.source = [thing(name='ELG: Project', url=project.url)]
            project = set_common_attributes(project, name, alternate_name, identifier, description, keywords, licences, in_language, country_of_origin, additional_type, version, date_published, date_modified)
            project.dateStart = date_published
            results['projects'].append(project)
            counter_retrieved_resources += 1
            continue
        elif result.entity_type == 'LanguageResource':
            if result.resource_type in ['Corpus', 'Lexical/Conceptual resource', 'Grammar']:
                dataset = Dataset()
                dataset = set_common_attributes(dataset, name, alternate_name, identifier, description, keywords, licences, in_language, country_of_origin, additional_type, version, date_published, date_modified)
                if result.resource_type == 'Corpus':
                    dataset.url = 'https://live.european-language-grid.eu/catalogue/corpus/' + str(result.id)
                    dataset.source = [thing(name='ELG: Corpus', url=dataset.url)]
                elif result.resource_type == 'Lexical/Conceptual resource':
                    dataset.url = 'https://live.european-language-grid.eu/catalogue/lcr/' + str(result.id)
                    dataset.source = [thing(name='ELG: Lexical/Conceptual resource', url=dataset.url)]
                elif result.resource_type == 'Grammar':
                    dataset.url = 'https://live.european-language-grid.eu/catalogue/ld/' + str(result.id)
                    dataset.source = [thing(name='ELG', url=dataset.url)]
                results['resources'].append(dataset)
                counter_retrieved_resources += 1
                continue
            elif result.resource_type in ['Tool/Service', 'Model']:
                software = SoftwareApplication()
                software = set_common_attributes(software, name, alternate_name, identifier, description, keywords, licences, in_language, country_of_origin, additional_type, version, date_published, date_modified)
                if result.resource_type == 'Tool/Service':
                    software.url = 'https://live.european-language-grid.eu/catalogue/tool-service/' + str(result.id)
                    software.source = [thing(name='ELG: Tool/Service', url=software.url)]
                elif result.resource_type == 'Model':
                    software.url = 'https://live.european-language-grid.eu/catalogue/ld/' + str(result.id)
                    software.source = [thing(name='ELG', url=software.url)]
                results['resources'].append(software)
                counter_retrieved_resources += 1
                continue

        creative_work = CreativeWork()
        creative_work.url = 'https://live.european-language-grid.eu/catalogue/ld/' + str(result.id)
        creative_work.source = [thing(name='ELG', url=creative_work.url)]
        creative_work = set_common_attributes(creative_work, name, alternate_name, identifier, description, keywords, licences, in_language, country_of_origin, additional_type, version, date_published, date_modified)
        results['others'].append(creative_work)
        counter_retrieved_resources += 1

    utils.log_event(type="info", message=f"{source} - retrieved {counter_retrieved_resources} results.")
    print(f"{source} - retrieved {counter_retrieved_resources} results.")
