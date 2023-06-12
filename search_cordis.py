import requests
from objects import Cordis
import logging
import os

logger = logging.getLogger('nfdi_search_engine')

def cordis(search_term, results):
    api_url = f'https://cordis.europa.eu/search/?q=%27{search_term}%27%20AND%20contenttype=%27project%27&p=1&num=10&srt=/project/contentUpdateDate:decreasing&format=json'
    response = requests.get(api_url)
    
    logger.debug(f'Gesis response status code: {response.status_code}')
    logger.debug(f'Gesis response headers: {response.headers}')

    data = response.json()
    
    try:
        hits = data.get('hits', {}).get('hit', [])
    except AttributeError:
        hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

    for hit in hits:

        try:
            if isinstance(hit, dict):
                project = hit.get('project', {})
                id = project.get('id', '')
                title = project.get('title', '')
                url = f"https://cordis.europa.eu/project/id/{id}"
                start_date = project.get('startDate', '')
                end_date = project.get('endDate', '')
                summary = project.get('teaser', '')
            else:
                # Handle the case when `hit` is not a dictionary
                project = {}
                id = ''
                title = ''
                url = ''
                start_date = ''
                end_date = ''
                summary = ''

        except KeyError as e:
            # Handle the exception when the key is not found
            print(f"KeyError: {e} - Key not found in API response")
            # Set default none
            id = None
            title = None
            url = None
            start_date = None
            end_date = None
            summary = None


        results.append(
                Cordis(
                    id=id,
                    url=url,
                    date=f'From: {start_date} - To: {end_date}',
                    title=title,
                    description=summary
                )
            )
  
    logger.info(f'Got {len(results)} records from Cordis') 