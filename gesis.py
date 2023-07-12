import requests
from objects import Gesis, Article, Dataset
import logging
import os
from objects import Dataset, Article
import re
import utils

logger = logging.getLogger('nfdi_search_engine')


def search(search_term, results):
    # API URL with the search term
    api_url = f'http://193.175.238.35:8089/dc/_search?q={search_term}'

    try:
        # Send a GET request to the API URL
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for non-successful response status codes

        logger.debug(f'Gesis response status code: {response.status_code}')
        logger.debug(f'Gesis response headers: {response.headers}')

        data = response.json()

        try:
            # Extract the 'hits' array from the response data
            hits = data.get('hits', {}).get('hits', [])
        except AttributeError:
            hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError

        # Iterate through the hits array and extract the dc fields
        for hit in hits:
            try:
                # Extract the dc fields from the hit object
                dc_fields = hit['_source']['dc']

                # Extract the desired fields from the dc object
                doi = dc_fields['relation']['nn'][0] if 'relation' in dc_fields and 'nn' in dc_fields['relation'] else 'Unknown DOI'
                title = dc_fields['title']['all'][0] if 'title' in dc_fields and 'all' in dc_fields['title'] else ''
                
                authors = ''
                if 'creator' in dc_fields and 'all' in dc_fields['creator']:
                    authors = dc_fields['creator']['all'][0]
                authors_list = '; '.join(authors for authors in dc_fields['creator']['all']) if authors else ''
                
                description = dc_fields['description']['all'][0] if 'description' in dc_fields and 'all' in dc_fields['description'] else ''
                short_description = utils.remove_html_tags(description)
                type = dc_fields['type']['all'][0] if 'type' in dc_fields and 'all' in dc_fields['type'] else 'Type not available'
                date = dc_fields['date']['nn'][0] if 'date' in dc_fields and 'nn' in dc_fields['date'] else ''
                id = hit['_id']
                id = id.replace('.', '-')
                url = f"https://search.gesis.org/research_data/datasearch-{id}"

                if type == "Dataset":
                    # Create a Dataset object and append it to the results list
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
                    # Create an Article object and append it to the results list
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
            except KeyError as e:
                # Handle the case when a key is not found in the response
                logger.warning(f"Key not found in the response: {e}. Skipping this hit.")
            except IndexError as e:
                # Handle the case when an index is out of range
                logger.warning(f"Index out of range: {e}. Skipping this hit.")
    except requests.exceptions.RequestException as e:
        # Handle any errors that occur while making the API request
        logger.error(f"Error occurred while making the API request: {e}")
    except ValueError as ve:
        # Handle errors that occur while parsing the response JSON
        logger.error(f"Error occurred while parsing the response JSON: {ve}")

    logger.info(f'Got {len(results)} records from Gesis')