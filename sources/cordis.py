import requests
from objects import Project
import logging
import os
import utils

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
                                        fundings.availableLanguages.append(language)
                                else:
                                    # If languages is a single string, directly append it to fundings.inLanguage
                                    fundings.availableLanguages.append(languages_available)

                    else:
                        # Handle the case when `hit` is not a dictionary
                        fundings = Project()
                        fundings.identifier = ''
                        fundings.name = ''
                        fundings.url = ''
                        fundings.date_start = ''
                        fundings.date_end = ''
                        fundings.description = ''

                except KeyError as e:
                    # Handle the exception when the key is not found
                    print(f"KeyError: {e} - Key not found in API response")
                    # Set default none
                    fundings.identifier = None
                    fundings.name = None
                    fundings.url = None
                    fundings.date_start = None
                    fundings.date_end = None
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