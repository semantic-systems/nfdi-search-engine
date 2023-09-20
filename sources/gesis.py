import requests
import logging
import os
from objects import Dataset, Person
import re
import utils

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    try:

        # API URL with the search term
        api_url = f'http://193.175.238.35:8089/dc/_search?q={search_term}&size=100'
        # Send a GET request to the API URL
        # response = requests.get(api_url)
        response = requests.get(api_url, timeout=3)
        response.raise_for_status()  # Raise an exception for non-successful response status codes

        logger.debug(f'Gesis response status code: {response.status_code}')
        logger.debug(f'Gesis response headers: {response.headers}')

        data = response.json()

        try:
            # Extract the 'hits' array from the response data
            hits = data.get('hits', {}).get('hits', [])
            total_hits = data.get('hits', {}).get('total', '')
            logger.info(f'Gesis - {total_hits} hits/records found')
        except AttributeError:
            hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

        # Iterate through the hits array and extract the dc fields
        for hit in hits:
            try:
                # Extract the dc fields from the hit object
                dc_fields = hit['_source']['dc']
                resources = Dataset()
                resources.source = 'GESIS'
                # Extract the desired fields from the dc object
                doi = dc_fields['relation']['nn'][0] if 'relation' in dc_fields and 'nn' in dc_fields['relation'] else 'Unknown DOI'
                title = dc_fields['title']['all'][0] if 'title' in dc_fields and 'all' in dc_fields['title'] else ''
                resources.name =title 
                description = dc_fields['description']['all'][0] if 'description' in dc_fields and 'all' in dc_fields['description'] else ''
                short_description = utils.remove_html_tags(description)
                resources.abstract = short_description
                resources.description = short_description
                type = dc_fields['type']['all'][0] if 'type' in dc_fields and 'all' in dc_fields['type'] else 'Type not available'
                date_published = dc_fields['date']['nn'][0] if 'date' in dc_fields and 'nn' in dc_fields['date'] else ''
                resources.datePublished = date_published
                # publisher = dc_fields['publisher']['all'][0] if 'publisher' in dc_fields and 'all' in dc_fields['publisher'] else None
                # resources.publisher=publisher

                # rights = dc_fields['rights']['all'][0] if 'rights' in dc_fields and 'all' in dc_fields['rights'] else None
                # resources.license = rights

                languages = dc_fields['language']['all'] if 'language' in dc_fields and 'all' in dc_fields['language'] else ''
                if languages:
                    for language in languages:
                        resources.inLanguage.append(language)
                
                id = hit['_id']
                id = id.replace('.', '-')
                url = f"https://search.gesis.org/research_data/datasearch-{id}"
                resources.url=url

                for creator in dc_fields.get('creator', {}).get("all", []):
                        author = Person()
                        author.type = "Person" # there is not type for creator in Gesis it's jus for now
                        author.name = creator
                        resources.author.append(author)
         
                results['resources'].append(resources)

            except KeyError as e:
                # Handle the case when a key is not found in the response
                logger.warning(f"Key not found in the response: {e}. Skipping this hit.")
            except IndexError as e:
                # Handle the case when an index is out of range
                logger.warning(f"Index out of range: {e}. Skipping this hit.")
    # except requests.exceptions.RequestException as e:
    #     # Handle any errors that occur while making the API request
    #     logger.error(f"Error occurred while making the API request: {e}")
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
    