
import requests
from objects import Gesis, Article, Dataset
import logging
import os
import requests
from objects import Dataset, Article

logger = logging.getLogger('nfdi_search_engine')

def gesis(search_term, results):

    api_url = f'http://193.175.238.35:8089/dc/_search?q={search_term}'
    # api_url = f'http://193.175.238.35:8089/_search?q={search_term}'
    response = requests.get(api_url)

    logger.debug(f'Gesis response status code: {response.status_code}')
    logger.debug(f'Gesis response headers: {response.headers}')
    
    response = requests.get(api_url)
    data = response.json()

   
    try:
        hits = data.get('hits', {}).get('hits', [])
    except AttributeError:
        hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

    # Iterate through the hits array and extract the dc fields
    for hit in hits:
            dc_fields = hit['_source']['dc']

            # Extract the desired fields from the dc object
            if 'relation' in dc_fields:
                doi = dc_fields['relation']['nn'][0]
            else:
                doi = 'Unknown DOI'

        
            title = dc_fields.get('title', {}).get('all', [""])[0]
            authors = dc_fields.get('creator', {}).get('all', [""])
            description = dc_fields.get('description', {}).get('all', [""])[0]
            type = dc_fields.get('type', {}).get('all', [""])[0]
            date = dc_fields.get('date', {}).get('nn', [""])[0]
            id = hit['_id']
            id = id.replace('.', '-')
            url = f"https://search.gesis.org/research_data/datasearch-{id}"
           
            if (type == "Dataset"):
                results.append(
                    Dataset(
                            title=title, 
                            url=url,
                            authors=authors,
                            description=description, 
                            date=date
                            
                    )
                )
            elif (type == "Article"):
                results.append(
                    Article(
                            title=title, 
                            url=url,
                            authors=authors,
                            description=description, 
                            date=date, 
                            # doi=doi, 
                            
                    )
                )
     
    logger.info(f'Got {len(results)} records from Gesis') 