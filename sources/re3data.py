import time
from typing import Iterable, Dict, Any, List

import utils
from objects import Dataset, Organization
from config import Config
from sources import data_retriever
from objects import thing, Author, Article

from sources.base import BaseSource


class RE3DATA(BaseSource):
    """
    Search for repositories in the Re3Data registry based on the search term. For re3data, the returned search results
    are only short models of repositories and do not contain detailed information, since very limited information
    is returned by the search-term-ready API and looping over all details is too time-consuming.
    """

    SOURCE = 'RE3DATA'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_url = Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', '')
        search_results = data_retriever.retrieve_data(
            source=self.SOURCE,
            base_url=search_url,
            search_term=search_term,
            failed_sources=failed_sources
        )
        return search_results
    

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """

        repositories = raw.get('list', {}).get('repository', [])
        if isinstance(repositories, dict):
            repositories = [repositories]

        repositories_to_parse = repositories[:Config.NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT]
        self.log_event(type="info", message=f"{self.SOURCE} - {len(repositories)} records matched; pulled top {len(repositories_to_parse)}")   
        return repositories_to_parse
    

    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """

        repository = Dataset(
            name=hit.get('name', ''),
            identifier=hit.get('doi', '').partition('doi.org/')[2],
            url=hit.get('link', {}).get('@href', ''),
            source=[thing(name=self.SOURCE, url=hit.get('doi', ''), identifier=hit.get('link', {}).get('@href', '').partition('https://www.re3data.org/api/beta/repository/')[2])],
            partiallyLoaded=True,
        )

        return repository
    
    def map_hit_detailled(self, source: str, hit: dict, doi: str) -> Dataset:
        """
        Map the detailed information of a repository to a Dataset object.

        :param source: the source of the information about the repository (re3data)
        :param hit: the detailed information of the repository from the API
        :param doi: the DOI of the repository

        :return: Dataset - repository in the form of a dataset object
        """
        repository_data = hit.get('r3d:re3data', {}).get('r3d:repository', {})

        institutions = repository_data.get('r3d:institution', [])
        if isinstance(institutions, dict):
            institutions = [institutions]

        def get_alternate_names(additional_names) -> List[str]:
            if isinstance(additional_names, dict):
                return [additional_names.get('#text', '')]
            return []

        organizations = []

        for inst in institutions:

            # identifier must be a single instance (no lists)
            institutionIdentifier = inst.get('r3d:institutionIdentifier', '')
            if type(institutionIdentifier) == list:
                identifier = institutionIdentifier[0]
            else:
                identifier = institutionIdentifier
            
            # keywords must be a list
            responsibilityType = inst.get('r3d:responsibilityType', [])
            if type(responsibilityType) == list:
                keywords = responsibilityType
            else:
                keywords = [responsibilityType]

            organization = Organization(
                name=inst.get('r3d:institutionName', {}).get('#text', ''),
                alternateName=get_alternate_names(inst.get('r3d:institutionAdditionalName', {})),
                additionalType=inst.get('r3d:institutionType', ''),
                url=inst.get('r3d:institutionURL', ''),
                identifier=identifier,
                location=inst.get('r3d:institutionCountry', ''),
                email=inst.get('r3d:institutionContact', ''),
                keywords=keywords,
                source=[thing(name=source,
                            url='https://www.re3data.org/repository/' +
                                repository_data.get('r3d:re3data.orgIdentifier', ""))]
            )
            organizations.append(organization)

        # funder must be a single instance, so we only take the first entity
        funder = [org for org in organizations if 'funding' in org.keywords][0]

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
        
        # genre expects a string, so we concatenate subjects
        genre = ', '.join(subjects)

        return Dataset(
            name=repository_data.get('r3d:repositoryName', {}).get('#text', ''),
            alternateName=get_alternate_names(repository_data.get('r3d:additionalName', {})),
            description=repository_data.get('r3d:description', {}).get('#text', ''),
            url=repository_data.get('r3d:repositoryURL', ""),
            identifier=doi,
            additionalType=', '.join(content_types),
            source=[thing(name=source,
                        identifier=repository_data.get('r3d:re3data.orgIdentifier', ""),
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
            genre=genre,
            text=repository_data.get('r3d:remarks', "")
        )
    

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        for hit in hits:
            repository = self.map_hit(hit)

            if repository:
                results['resources'].append(repository)

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources, tracking=None):
    """
    Entrypoint to search RE3DATA dataset.
    """
    RE3DATA(tracking).search(source, search_term, results, failed_sources)

@utils.handle_exceptions
def get_resource(source: str, source_identifier: str, doi: str, tracking=None):
    """
    Retrieve detailed information for the repository. 

    :param source: source label for the data source; in this case its re3data
    :param source_identifier: the primay identifier in the source records
    :param doi: digital identifier for the resource

    :return: dataset
    """

    re3data = RE3DATA(tracking)

    base_url = Config.DATA_SOURCES[source].get('get-resource-endpoint', '')     
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=base_url,
                                                    identifier=source_identifier) #source identifier will be passed on with the base url
    if search_result:
        dataset = re3data.map_hit_detailled(source, search_result, doi)
        tracking.log_event_async(log_type="info", message=f"{source} - retrieved repository details")
        return dataset
