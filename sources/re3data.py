import requests
import utils
from objects import CreativeWork, Organization
import logging
import xmltodict
from main import app
logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_string: str, results):
    re3data_product_search(search_string, results)

    logger.info(f"Got {len(results)} records from re3data")
    return results


def re3data_product_search(search_string, results):
    try:
        api_url = 'https://www.re3data.org/api/beta/repositories'
        response = requests.get(api_url,
                                params={"query": search_string}, timeout=int(app.config["REQUEST_TIMEOUT"])
                                )
        # Response comes as XML
        data = xmltodict.parse(response.content)

        logger.debug(f're3data product search response status code: {response.status_code}')
        logger.debug(f're3data product search response headers: {response.headers}')

        if response.status_code == 200:
            try:
                hits = data.get('list', {}).get('repository', [])
            except AttributeError:
                hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

            for hit in hits:
                repo_uri = hit.get('link', {}).get('@href', '')
                try:
                    # if repo_uri != "":
                    hit_response = requests.get(repo_uri)
                    hit_data = xmltodict.parse(hit_response.content)
                    hit_details = hit_data.get('r3d:re3data', {}).get('r3d:repository', {})
                    repository = CreativeWork()
                    repository.source = 're3data'
                    repo_id = hit_details.get('r3d:re3data.orgIdentifier', None)
                    if repo_id is not None:
                        repository.url = 'https://www.re3data.org/repository/' + repo_id
                    repository.name = hit_details.get('r3d:repositoryName', {}).get('#text', '')
                    alternate_names = hit_details.get('r3d:additionalName', None)
                    if isinstance(alternate_names, dict):
                        repository.alternateName = alternate_names.get('#text', '')
                    elif isinstance(alternate_names, list):
                        item_list = []
                        for alternate_name in alternate_names:
                            item_list.append(alternate_name.get('#text'))
                        repository.alternateName = ' - '.join(item_list)
                    repository.description = utils.remove_line_tags(
                        hit_details.get('r3d:description', {}).get('#text', ''))

                    # Not showing identifiers on result page
                    # repository.identifier = hit_details.get('r3d:repositoryIdentifier', '')

                    repository.dateCreated = hit_details.get('r3d:startDate', '')
                    repository.datePublished = hit_details.get('r3d:entryDate', '')
                    repository.dateModified = hit_details.get('r3d:lastUpdate''')
                    repository.keywords = hit_details.get('r3d:keyword', '')
                    repository.inLanguage = [hit_details.get('r3d:repositoryLanguage', '')]

                    # Not showing licenses on result page
                    # licenses = hit_details.get('r3d:dataLicense', None)
                    # if type(licenses) is dict:
                    #     repository.license = licenses.get('r3d:dataLicenseURL', '')
                    # elif type(licenses) is list:
                    #     license_list = []
                    #     for item in licenses:
                    #         license_list.append(item.get('r3d:dataLicenseURL', ''))
                    #         repository.license = license_list

                    institutions = hit_details.get('r3d:institution', None)
                    if isinstance(institutions, dict):
                        organization = Organization()
                        organization.name = institutions.get('r3d:institutionName', {}).get('#text', '')
                        organization.alternateName = institutions.get('r3d:institutionAdditionalName', {}).get(
                            '#text', '')
                        organization.location = institutions.get('r3d:institutionCountry', '')
                        organization.url = institutions.get('r3d:institutionURL', '')
                        if 'funding' in institutions.get('r3d:responsibilityType', []):
                            repository.funder = organization
                        else:
                            repository.sourceOrganization = organization

                    elif isinstance(institutions, list):
                        funder_list, sourceOrga_list = [], []
                        for institution in institutions:
                            organization = Organization()
                            organization.name = institution.get('r3d:institutionName', {}).get('#text', '')
                            additional_names = institution.get('r3d:institutionAdditionalName', None)
                            if isinstance(additional_names, list):
                                name_list = []
                                for additional_name in additional_names:
                                    name_list.append(additional_name.get('#text', ''))
                                organization.alternateName = ", ".join(name_list)
                            elif isinstance(additional_names, str):
                                organization.alternateName = additional_names
                            organization.location = institution.get('r3d:institutionCountry', '')
                            organization.url = institution.get('r3d:institutionURL', '')
                            if 'funding' in institution.get('r3d:responsibilityType', None):
                                funder_list.append(organization)
                            else:
                                sourceOrga_list.append(organization)
                        repository.funder = funder_list
                        repository.sourceOrganization = sourceOrga_list
                    results['resources'].append(repository)

                # Exception if no url to call Details API
                except Exception as ex:
                    logger.error(f'Exception: {str(ex)}')

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('re3data')

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
