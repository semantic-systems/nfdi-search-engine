import requests
from objects import Project
import logging
import os
import utils

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    max_project_number = 50
    api_url = f'https://cordis.europa.eu/search/?q=%27{search_term}%27%20AND%20contenttype=%27project%27&p=1&num={max_project_number}&srt=/project/contentUpdateDate:decreasing&format=json'
    response = requests.get(api_url)
    
    # Check if the response was successful
    if response.status_code == 200:
        logger.debug(f'Cordis response status code: {response.status_code}')
        logger.debug(f'Cordis response headers: {response.headers}')

        data = response.json()

        total_hits = data.get('result', {}).get('header', {}).get('totalHits', 0)

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
                        resources = Project()
                        resources.source = 'CORDIS'
                        resources.identifier = project.get('id', '')
                        resources.name = project.get('title', '')
                        resources.url = f"https://cordis.europa.eu/project/id/{resources.identifier}"
                        resources.dateStart = project.get('startDate', '')
                        resources.dateEnd = project.get('endDate', '')
                        resources.dateLastModified = project.get('lastUpdateDate', '')
                        resources.description = project.get('teaser', '')
                        # this key attribute can be used for the details page of the resource tab in next step
                        # it has more detais about projects
                        resources.objective = project.get("objective", '')
                        resources.status = project.get("status", '')

                        keywords = project.get("keywords", None)
                        if keywords:
                            for keyword in keywords:
                                resources.keywords.append(keyword)

                        languages = project.get("language", None)
                        if languages:
                            if isinstance(languages, list):
                                # If languages is a list, add each language to resources.inLanguage
                                for language in languages:
                                    resources.inLanguage.append(language)
                            else:
                                # If languages is a single string, directly append it to resources.inLanguage
                                resources.inLanguage.append(languages)

                        languages_available = project.get("availableLanguages", None)
                        if languages_available:
                            if isinstance(languages_available, list):
                                # If languages_available is a list, add each language to resources.languages_available
                                for language in languages_available:
                                    resources.availableLanguages.append(language)
                            else:
                                # If languages is a single string, directly append it to resources.inLanguage
                                resources.availableLanguages.append(languages_available)

                else:
                    # Handle the case when `hit` is not a dictionary
                    resources = Project()
                    resources.identifier = ''
                    resources.name = ''
                    resources.url = ''
                    resources.date_start = ''
                    resources.date_end = ''
                    resources.description = ''

            except KeyError as e:
                # Handle the exception when the key is not found
                print(f"KeyError: {e} - Key not found in API response")
                # Set default none
                resources.identifier = None
                resources.name = None
                resources.url = None
                resources.date_start = None
                resources.date_end = None
                resources.description = None


            results['resources'].append(resources)
           
    

        logger.info(f'Got {len(results)} records from Cordis') 

    else:
        # Log an error message when the response is not successful
        logger.error(f'Cordis response status code: {response.status_code}. Unable to fetch data from the API.')