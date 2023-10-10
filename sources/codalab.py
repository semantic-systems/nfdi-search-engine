import requests
import datetime
import logging
import os
from objects import Dataset, Person
import utils

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    try:

        url = "https://worksheets.codalab.org/rest/bundles"
        limit_per_page = 10
        params = {
            "keywords": search_term,
            "include_display_metadata": 1,
            "include": "owner",
            ".limit": limit_per_page
        }
        # Send an HTTP GET request to the API
        # response = requests.get(api_endpoint, params=params)
        response = requests.get(url, timeout=3)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            response_data = response.json()

            logger.debug(f'Codalab response status code: {response.status_code}')
            logger.debug(f'Codalab response headers: {response.headers}')

            # Extract the 'data' list from the response
            bundles_data = response_data.get("data", [])
            bundles_includes = response_data.get("included", [])

            if bundles_data:
                # Loop through each bundle in 'data' and extract the required information
                for bundle in bundles_data:
                    type = bundle['type']
                    if type == "bundles":
                        resources = Dataset()
                        resources.source = 'CODALAB'
                        # Extract the bundle information
                        resources.identifier = bundle['id']
                        resources.name = bundle["attributes"]["metadata"]["name"]
                        resources.license = bundle.get("attributes", {}).get("metadata", {}).get("license", "")
                        resources.description  = bundle.get("attributes", {}).get("metadata", []).get("description", "")
                        date_created = bundle.get("attributes", {}).get("metadata", []).get("created")
                        # Check if date_created is not None before attempting to convert to a timestamp
                        if date_created is not None:
                            resources.dateCreated = datetime.datetime.fromtimestamp(date_created).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            # Handle the case when date_created is None set it to empty
                            resources.dateCreated = ''  
                        
                        # Check if bundle is not None before accessing its keys
                        if bundle is not None:
                        # Check if relationships is not None before accessing its keys
                            relationships = bundle.get("relationships")
                            if relationships is not None:
                                # Check if owner is not None before accessing its keys
                                owner = relationships.get("owner")
                                if owner is not None:
                                    # Check if data is not None before accessing its keys
                                    data = owner.get("data")
                                    if data is not None:
                                        author_owner_id = data.get("id", "")
                                    else:
                                        author_owner_id = ""  
                                else:
                                    author_owner_id = ""  
                            else:
                                author_owner_id = ""  
                        else:
                            author_owner_id = ""  

                        # link URL to the bundle
                        resources.url = f"https://worksheets.codalab.org/bundles/{resources.identifier}"

                        parent_uuid = None
                        # Check if the bundle has dependencies
                        if bundle.get("attributes", {}).get("dependencies"):
                            parent_uuid = bundle["attributes"]["dependencies"][0]["parent_uuid"]
                            parent_uuid_url = f"https://worksheets.codalab.org/bundles/{parent_uuid}"

                        # Find the corresponding owner information from 'bundles_includes' using the author_owner_id
                        for include in bundles_includes:
                            if include.get('id') == author_owner_id:
                                author = Person()
                                author.type = "Person"

                                owner_user_name = include.get('attributes', {}).get('user_name', "")
                                owner_givenName = include.get('attributes', {}).get('first_name', "")
                                owner_familyName = include.get('attributes', {}).get('last_name', "")

                                # Check if owner_user_name is available and not empty
                                if owner_user_name:
                                    author.name = owner_user_name
                                # Check if owner_familyName is available and not empty
                                elif owner_familyName:
                                    author.name = owner_familyName
                                # Check if owner_givenName is available and not empty
                                elif owner_givenName:
                                    author.name = owner_givenName
                                else:
                                    # If none of the above conditions are met, set author_name to an empty string
                                    author.name = ""

                                # append the author_name to the author object
                                resources.author.append(author)

                        results['resources'].append(resources)

                logger.info(f'Got {len(results)} records from Codalab')
            else:
                # Log an error message when the response is not successful
                logger.error(f'Codalab response status code: {response.status_code}. No data for the search term found.')
        else:
        # Log an error message when the response is not successful
            logger.error(f'Codalab response status code: {response.status_code}. Unable to fetch data from the API.')
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('CODALAB')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')