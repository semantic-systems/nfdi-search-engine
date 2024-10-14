from elg.utils.errors import ensure_response_ok

from objects import thing, Dataset, SoftwareApplication, Organization, Project, CreativeWork
import utils
from elg import Catalog
from elg.entity import Entity

import urllib
from typing import List, Dict
import requests
from main import app

import logging

from sources import data_retriever

logger = logging.getLogger('nfdi_search_engine')





@utils.handle_exceptions
def search(source: str, search_term: str, results: Dict, failed_sources: List):

    class CatalogDataRetriever(Catalog):

        def _get(self, path: str, queries: List[set] = None, json: bool = False):
            """
            Internal method to call the API
            """

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
                                                    clean_json=False)
            return response


    catalog = CatalogDataRetriever()
    elg_results = catalog.search(
        search=search_term,
        limit=100
    )
    for result in elg_results:
        licences = ', '.join(set(result.licences))
        description = utils.remove_html_tags(result.description)
        name = result.resource_name
        date_published = str(result.creation_date)
        date_modified = str(result.last_date_updated)
        keywords = result.keywords
        if isinstance(keywords, dict):
            for keyword in keywords.get('buckets', []):
                for items in keyword:
                    keywords.append(items['key'])
        if hasattr(result, 'media_type') and isinstance(result.media_type, list):
            keywords.extend(result.media_type)

        in_language = result.languages
        if isinstance(in_language, dict):
            for language in in_language.get('buckets', []):
                for items in language:
                    in_language.append(items['key'])

        country_of_origin = result.country_of_registration
        additional_type = result.resource_type
        if hasattr(result, 'version'):
            version = result.version #TODO check if version in classes set
        alternate_name = result.resource_short_name
        identifier = result.id

        if result.entity_type == 'Organization':
            organization = Organization()
            organization.url = 'https://live.european-language-grid.eu/catalogue/organization/' + str(result.id)
            organization.source = [thing(name='ELG: Organization',
                                         url=organization.url)]
            organization.name = name
            organization.alternateName = alternate_name
            organization.identifier = identifier
            organization.description = description
            organization.keywords = keywords
            organization.license = licences
            organization.inLanguage = in_language
            organization.countryOfOrigin = country_of_origin
            organization.additionalType = additional_type
            organization.version = version
            organization.datePublished = date_published
            organization.dateModified = date_modified
            organization.location = str(set(result.country_of_registration))
            results['organizations'].append(organization)
        elif result.entity_type == 'Project':
            project = Project()
            project.url = 'https://live.european-language-grid.eu/catalogue/project/' + str(result.id)
            project.source = [thing(name='ELG: Project',
                                    url=project.url)]
            project.name = name
            project.alternateName = alternate_name
            project.identifier = identifier
            project.description = description
            project.keywords = keywords
            project.license = licences
            project.inLanguage = in_language
            project.countryOfOrigin = country_of_origin
            project.additionalType = additional_type
            project.version = version
            project.datePublished = date_published
            project.dateModified = date_modified
            results['projects'].append(project)
        elif result.entity_type == 'LanguageResource':
            if result.resource_type in ['Corpus', 'Lexical/Conceptual resource', 'Grammar']:
                dataset = Dataset()
                dataset.name = name
                dataset.alternateName = alternate_name
                dataset.identifier = identifier
                dataset.description = description
                dataset.keywords = keywords
                dataset.license = licences
                dataset.inLanguage = in_language
                dataset.countryOfOrigin = country_of_origin
                dataset.additionalType = additional_type
                dataset.version = version
                dataset.datePublished = date_published
                dataset.dateModified = date_modified
                if result.resource_type == 'Corpus':
                    dataset.url = 'https://live.european-language-grid.eu/catalogue/corpus/' + str(result.id)
                    dataset.source = [thing(name='ELG: Corpus',
                                            url=dataset.url)]
                elif result.resource_type == 'Lexical/Conceptual resource':
                    dataset.url = 'https://live.european-language-grid.eu/catalogue/lcr/' + str(result.id)
                    dataset.source = [thing(name='ELG: Lexical/Conceptual resource',
                                            url=dataset.url)]
                elif result.resource_type == 'Grammar':
                    dataset.url = 'https://live.european-language-grid.eu/catalogue/ld/' + str(result.id)
                    dataset.source = [thing(name='ELG: Grammar',
                                            url=dataset.url)]
                results['resources'].append(dataset)
            elif result.resource_type in ['Tool/Service', 'Model']:
                software = SoftwareApplication()
                software.name = name
                software.alternateName = alternate_name
                software.identifier = identifier
                software.description = description
                software.keywords = keywords
                software.license = licences
                software.inLanguage = in_language
                software.countryOfOrigin = country_of_origin
                software.additionalType = additional_type
                software.version = version if version else None
                software.datePublished = date_published
                software.dateModified = date_modified
                if result.resource_type == 'Tool/Service':
                    software.url = 'https://live.european-language-grid.eu/catalogue/tool-service/' + str(result.id)
                    software.source = [thing(name='ELG: Tool/Service',
                                            url=software.url)]
                elif result.resource_type == 'Model':
                    software.url = 'https://live.european-language-grid.eu/catalogue/ld/' + str(result.id)
                    software.source = [thing(name='ELG: Model',
                                            url=software.url)]
                results['resources'].append(software)
        else:
            creative_work = CreativeWork()
            creative_work.url = 'https://live.european-language-grid.eu/catalogue/ld/' + str(result.id)
            creative_work.source = [thing(name='ELG: Other Language Description',
                                     url=creative_work.url)]
            creative_work.name = name
            creative_work.alternateName = alternate_name
            creative_work.identifier = identifier
            creative_work.description = description
            creative_work.keywords = keywords
            creative_work.license = licences
            creative_work.inLanguage = in_language
            creative_work.countryOfOrigin = country_of_origin
            creative_work.additionalType = additional_type
            creative_work.version = version
            creative_work.datePublished = date_published
            creative_work.dateModified = date_modified
            results['others'].append(creative_work)

