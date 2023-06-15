import requests
from objects import Gesis, Article, Dataset
import logging
import os
from objects import Dataset, Article
import re

logger = logging.getLogger('nfdi_search_engine')

def search(search_term, results):

    api_url = f'http://193.175.238.35:8089/dc/_search?q={search_term}'
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

            title = dc_fields['title']['all'][0] if 'title' in dc_fields and 'all' in dc_fields['title'] else ''
            authors = dc_fields['creator']['all'][0] if 'creator' in dc_fields and 'all' in dc_fields['creator'] else ''
            authors_list = '; '.join(authors for authors in dc_fields['creator']['all'])
            description = dc_fields['description']['all'][0] if 'description' in dc_fields and 'all' in dc_fields['description'] else ''
            #extract the first two sentences from the description
            sentences = re.split(r'(?<=[.!?])\s+', description)
            short_description = ' '.join(sentences[:2])
            type = dc_fields['type']['all'][0] if 'type' in dc_fields and 'all' in dc_fields['type'] else 'Type not available'
            date = dc_fields['date']['nn'][0]
            id = hit['_id']
            id = id.replace('.', '-')
            url = f"https://search.gesis.org/research_data/datasearch-{id}"
           
            if type == "Dataset":
                results.append(
                    Dataset(
                            title=title, 
                            url=url,
                            authors=authors_list,
                            description=short_description, 
                            date=date
                            
                    )
                )
            elif type == "Article":
                results.append(
                    Article(
                            title=title, 
                            url=url,
                            authors=authors_list,
                            description=short_description, 
                            date=date, 
                            # doi=doi, 
                            
                    )
                )
     
    logger.info(f'Got {len(results)} records from Gesis')