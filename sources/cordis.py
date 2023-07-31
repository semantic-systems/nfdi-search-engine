import requests
from objects import Project
import logging
import os
import utils

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    api_url = f'https://cordis.europa.eu/search/?q=%27{search_term}%27%20AND%20contenttype=%27project%27&p=1&num=10&srt=/project/contentUpdateDate:decreasing&format=json'
    response = requests.get(api_url)
    
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
                resources = Project()
                resources.source = 'CORDIS'
                project = hit.get('project', {})
                resources.identifier = project.get('id', '')
                resources.name = project.get('title', '')
                resources.url = f"https://cordis.europa.eu/project/id/{id}"
                resources.date_start = project.get('startDate', '')
                resources.date_end = project.get('endDate', '')
                resources.description = project.get('teaser', '')
            else:
                # Handle the case when `hit` is not a dictionary
                project = {}
                resources.identifier = ''
                resources.name = ''
                resources.url = ''
                resources.date_start = ''
                resources.date_end = ''
                resources.abstract = ''

        except KeyError as e:
            # Handle the exception when the key is not found
            print(f"KeyError: {e} - Key not found in API response")
            # Set default none
            resources.identifier = None
            resources.name = None
            resources.url = None
            resources.date_start = None
            resources.date_end = None
            resources.abstract = None


        results['resources'].append(resources)
        # results.append(
        #         Cordis(
        #             id=id,
        #             url=url,
        #             date=f'From: {start_date} - To: {end_date}',
        #             title=title,
        #             description=summary
        #         )
        #     )
  
    logger.info(f'Got {len(results)} records from Cordis') 