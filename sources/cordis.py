import requests
from objects import Project
import logging
import os
import utils
import xml.etree.ElementTree as ET

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    try:

        max_project_number = 50
        api_url = f'https://cordis.europa.eu/search/?q=%27{search_term}%27%20AND%20contenttype=%27project%27&p=1&num={max_project_number}&srt=/project/contentUpdateDate:decreasing&format=json'
        # response = requests.get(api_url)
        response = requests.get(api_url, timeout=3)
        # response = timeout(requests.get, args=(api_url,), kwargs={'timeout': 10})
        
        # Check if the response was successful
        if response.status_code == 200:
            logger.debug(f'Cordis response status code: {response.status_code}')
            logger.debug(f'Cordis response headers: {response.headers}')

            data = response.json()

            total_hits = data.get('result', {}).get('header', {}).get('numHits', 0)

            logger.info(f'CORDIS - {total_hits} hits/records found')
            
            try:
                hits = data.get('hits', {}).get('hit', [])
            except AttributeError:
                hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

            for hit in hits:

                try:

                    if isinstance(hit, dict):
                        project = hit.get('project', {})
                        type = project.get('contenttype', '')

                        if type == "project":
                            fundings = Project()
                            fundings.source = 'CORDIS'
                            fundings.identifier = project.get('id', '')
                            fundings.name = project.get('title', '')
                            fundings.url = f"https://cordis.europa.eu/project/id/{fundings.identifier}"
                            fundings.dateStart = project.get('startDate', '')
                            fundings.dateEnd = project.get('endDate', '')
                            fundings.dateLastModified = project.get('lastUpdateDate', '')
                            fundings.description = project.get('teaser', '')
                            # this key attribute can be used for the details page of the resource tab in next step
                            # it has more detais about projects
                            fundings.objective = project.get("objective", '')
                            fundings.status = project.get("status", '')

                            keywords = project.get("keywords", None)
                            if keywords:
                                for keyword in keywords:
                                    fundings.keywords.append(keyword)

                            languages = project.get("language", None)
                            if languages:
                                if isinstance(languages, list):
                                    # If languages is a list, add each language to fundings.inLanguage
                                    for language in languages:
                                        fundings.inLanguage.append(language)
                                else:
                                    # If languages is a single string, directly append it to fundings.inLanguage
                                    fundings.inLanguage.append(languages)

                            languages_available = project.get("availableLanguages", None)
                            if languages_available:
                                if isinstance(languages_available, list):
                                    # If languages_available is a list, add each language to fundings.languages_available
                                    for language in languages_available:
                                        fundings.availableLanguage.append(language)
                                else:
                                    # If languages is a single string, directly append it to fundings.inLanguage
                                    fundings.availableLanguage.append(languages_available)

                    else:
                        # Handle the case when `hit` is not a dictionary
                        fundings = Project()
                        fundings.identifier = ''
                        fundings.name = ''
                        fundings.url = ''
                        fundings.dateStart = ''
                        fundings.dateEnd = ''
                        fundings.description = ''

                except KeyError as e:
                    # Handle the exception when the key is not found
                    print(f"KeyError: {e} - Key not found in API response")
                    # Set default none
                    fundings.identifier = None
                    fundings.name = None
                    fundings.url = None
                    fundings.dateStart = None
                    fundings.dateEnd = None
                    fundings.description = None


                results['fundings'].append(fundings)
            
        

            # logger.info(f'Got {len(results)} records from Cordis') 

        else:
            # Log an error message when the response is not successful
            logger.error(f'Cordis response status code: {response.status_code}. Unable to fetch data from the API.')
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('CORDIS')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')


#This function retrive deatials information of project from CORDIS
def project_details_cordis(project_id):
    
    try:
        # the URL of the XML data
        url = f"https://cordis.europa.eu/project/id/{project_id}?format=xml"

        # Send a GET request to the URL
        response = requests.get(url)

        # Check if the request was successful
        response.raise_for_status()

        # Parse the XML content and define namespaces
        namespaces = {"ns": "http://cordis.europa.eu"}
        root = ET.fromstring(response.content)

        # Create a Project instance
        project = Project()

        # Extract project information using namespaces
        project.source = 'CORDIS'
        project.identifier = root.find(".//ns:id", namespaces).text if root.find(".//ns:id", namespaces) is not None else None
        project.acronym = root.find(".//ns:acronym", namespaces).text if root.find(".//ns:acronym", namespaces) is not None else None
        project.name = root.find(".//ns:title", namespaces).text if root.find(".//ns:title", namespaces) is not None else None
        project.abstract = root.find(".//ns:teaser", namespaces).text if root.find(".//ns:teaser", namespaces) is not None else None
        project.objective = root.find(".//ns:objective", namespaces).text if root.find(".//ns:objective", namespaces) is not None else None
        project.totalCost = root.find(".//ns:totalCost", namespaces).text if root.find(".//ns:totalCost", namespaces) is not None else None
        project.dateStart = root.find(".//ns:startDate", namespaces).text if root.find(".//ns:startDate", namespaces) is not None else None
        project.dateEnd = root.find(".//ns:endDate", namespaces).text if root.find(".//ns:endDate", namespaces) is not None else None
        project.duration = root.find(".//ns:duration", namespaces).text if root.find(".//ns:duration", namespaces) is not None else None
        project.status = root.find(".//ns:status", namespaces).text if root.find(".//ns:status", namespaces) is not None else None
        project.keywords = root.find(".//ns:keywords", namespaces).text if root.find(".//ns:keywords", namespaces) is not None else None
        project.doi = root.find(".//ns:grantDoi", namespaces).text if root.find(".//ns:grantDoi", namespaces) is not None else None
        project.url = f'https://cordis.europa.eu/project/id/{project_id}'
        project.inLanguage = root.find(".//ns:language", namespaces).text if root.find(".//ns:language", namespaces) is not None else None

        # Find the category element with the specified attributes
        category_element = root.find(".//ns:category[@classification='source'][@type='isProvidedBy']", namespaces)

        if category_element is not None:
            available_languages_element = category_element.find(".//ns:availableLanguages", namespaces)
            if available_languages_element is not None:
                project.availableLanguage = available_languages_element.text if available_languages_element is not None else None
            else:
                project.availableLanguage = None
        else:
            project.availableLanguage = None

        # Find all organization elements with type="coordinator"
        coordinator_organizations = root.findall(".//ns:organization[@type='coordinator']", namespaces)

        coordinator_orgs_list = []

        for coordinator_organization in coordinator_organizations:
            coordinator_org = coordinator_organization.find(".//ns:legalName", namespaces)
            if coordinator_org is not None:
                coordinator_orgs_list.append(coordinator_org.text)
            else:
                coordinator_orgs_list.append(None)

        project.coordinatorOrganization = coordinator_orgs_list

        # Find the Sponsored by or Funded by program or organizaion
        programme_element = root.find(".//ns:programme[@type='relatedLegalBasis']", namespaces)
        if programme_element is not None:
            title_element = programme_element.find(".//ns:title", namespaces)
            if title_element is not None:
                project.funder = title_element.text
            else:
                project.funder = None
        else:
            project.funder = None

        # Find the region element
        region_element = root.find(".//ns:regions/ns:region[@type='relatedNutsCode']", namespaces)

        region_hierarchy = []

        while region_element is not None:
            region_name_element = region_element.find(".//ns:name", namespaces)
            if region_name_element is not None:
                region_name = region_name_element.text
                region_hierarchy.insert(0, region_name)
            parent_region_element = region_element.find(".//ns:parents/ns:region", namespaces)
            if parent_region_element is not None:
                region_element = parent_region_element
            else:
                region_element = None

        if region_hierarchy:
            complete_region = '  '.join(region_hierarchy)
            project.region = complete_region # region obj/property should be defined according to schema.org
        else:
            project.region = None

        return project

    except requests.exceptions.RequestException as e:
        print("Request Exception:", e)
    except ET.ElementTree.ParseError as e:
        print("XML Parse Error:", e)
    except Exception as e:
        print("An error occurred:", e)

    return None