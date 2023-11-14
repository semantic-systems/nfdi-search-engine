import requests
import utils
from objects import Dataset, Author, Article, CreativeWork, Organization, Project
import logging
import xmltodict

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
                                params={"query": search_string}  # ,  # , "format": "json", "size": 20},
                                , timeout=int(utils.config["request_timeout"])
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
                if repo_uri != "":
                    hit_response = requests.get(repo_uri)
                    hit_data = xmltodict.parse(hit_response.content)
                    hit_details = hit_data.get('r3d:re3data', {}).get('r3d:repository', {})
                    repository = CreativeWork()
                    repository.source = 're3data'
                    repo_id = hit_details.get('r3d:re3data.orgIdentifier', None)
                    if repo_id is not None:
                        repository.url = 'https://www.re3data.org/repository/' + repo_id
                    repository.name = hit_details.get('r3d:repositoryName', {}).get('#text', '')
                    alternate_name = hit_details.get('r3d:additionalName', None)
                    if type(alternate_name) is dict:
                        repository.alternateName = alternate_name.get('#text', '')
                    elif type(alternate_name) is list:
                        item_list = []
                        for item in alternate_name:
                            item_list.append(item.get('#text'))
                        repository.alternateName = ' - '.join(item_list)
                    repository.description = utils.remove_line_tags(
                        hit_details.get('r3d:description', {}).get('#text', ''))

                    # can be string or list:
                    repository.identifier = hit_details.get('r3d:repositoryIdentifier', '')
                    repository.dateCreated = hit_details.get('r3d:startDate', '')
                    repository.datePublished = hit_details.get('r3d:entryDate', '')
                    repository.dateModified = hit_details.get('r3d:lastUpdate''')
                    repository.keywords = hit_details.get('r3d:keyword', '')
                    repository.inLanguage = [hit_details.get('r3d:repositoryLanguage', '')]
                    licenses = hit_details.get('r3d:dataLicense', None)
                    if type(licenses) is dict:
                        repository.license = licenses.get('r3d:dataLicenseURL', '')
                    elif type(licenses) is list:
                        license_list = []
                        for item in licenses:
                            license_list.append(item.get('r3d:dataLicenseURL', ''))
                            repository.license = license_list

                    repo_institutions = hit_details.get('r3d:institution', None)
                    if type(repo_institutions) is dict:
                        organization = Organization()
                        organization.name = repo_institutions.get('r3d:institutionName', {}).get('#text', '')
                        organization.alternateName = repo_institutions.get('r3d:institutionAdditionalName', {}).get(
                            '#text', '')
                        organization.location = repo_institutions.get('r3d:institutionCountry', '')
                        organization.url = repo_institutions.get('r3d:institutionURL', '')
                        if 'funding' in repo_institutions.get('r3d:responsibilityType', []):
                            repository.funder = organization
                        else:
                            repository.sourceOrganization = organization

                    if type(repo_institutions) is list:
                        funder_list, sourceOrga_list = [], []
                        for item in repo_institutions:
                            print(item)
                            organization = Organization()
                            organization.name = item.get('r3d:institutionName', {}).get('#text', '')
                            additional_names = item.get('r3d:institutionAdditionalName', None)
                            if type(additional_names) is list:
                                name_list = []
                                for name in additional_names:
                                    name_list.append(name.get('#text', ''))
                                organization.alternateName = ",".join(name_list)
                            elif additional_names is str:
                                organization.alternateName = additional_names
                            organization.location = item.get('r3d:institutionCountry', '')
                            organization.url = item.get('r3d:institutionURL', '')
                            if 'funding' in item.get('r3d:responsibilityType', None):
                                funder_list.append(organization)
                            else:
                                sourceOrga_list.append(organization)
                        repository.funder = funder_list
                        repository.sourceOrganization = sourceOrga_list
                    results['resources'].append(repository)
                    print(repository)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('re3data')

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
