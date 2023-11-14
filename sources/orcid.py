import requests
import logging
from objects import Person, Author
import utils

logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):

    try:
                
        base_url = utils.config["search_url_orcid"]
        url = base_url + '"' + search_term.replace(' ', '+') + '"'
        
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'User-Agent': utils.config["request_header_user_agent"]
                   }

        response = requests.get(url, headers=headers, timeout=int(utils.config["request_timeout"]))

        if response.status_code == 200:
            search_result = response.json()

            records_found = search_result['num-found']
            logger.info(f'ORCID - {records_found} records found')

            if records_found > 0:
                authors = search_result.get('expanded-result', None)
                if authors:
                    for author in authors:
                
                        authorObj = Author()
                        authorObj.source = 'ORCID'
                        given_names = author.get('given-names', '')
                        family_names = author.get('family-names', '')
                        authorObj.name = given_names + " " + family_names
                        authorObj.orcid = author.get('orcid-id', '')

                        last_known_institution = author.get('institution-name', {})
                        if last_known_institution:
                            authorObj.affiliation = last_known_institution[-1]
                        else:
                            authorObj.affiliation = ''                    
                        authorObj.works_count = ''
                        authorObj.cited_by_count = ''

                        results['researchers'].append(authorObj)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('ORCID')
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')

def get_orcid_access_token():
    # Function to obtain the ORCID access token using client credentials
    token_url = 'https://orcid.org/oauth/token'
    client_id = 'APP-JJ5QRCFPR76FJCER'
    client_secret = 'cc4612d8-da98-49b4-ab3e-374d824a5fb1'
    scope = '/read-public'  # Specify the desired scope for accessing public data

    # Set the request body parameters
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scope
    }

    # Send the POST request to the token endpoint
    response = requests.post(token_url, data=data)

    if response.status_code == 200:
        # Extract the access token from the response JSON
        access_token = response.json().get('access_token')
        return access_token
    else:
        print("Failed to obtain access token:", response.text)
        return None
    
# Function to search for public information from ORCID
def old_search(search_term, results):
    # It also can be used for retrieving further information, logging in, edite records etc
    access_token = '45d5a287-de76-4a62-8ab9-1ffc046e7cde' 
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'nfdi4dsBot/1.0 (https://https://www.nfdi4datascience.de/nfdi4dsBot/; nfdi4dsBot@nfdi4datascience.de)'
    }
    search_url = 'https://pub.orcid.org/v3.0/search?q="' + search_term.replace(' ', '%20') + '"'

    try:
        # Send the GET request to search for public data
        response = requests.get(search_url, headers=headers, timeout=int(utils.config["request_timeout"]))

        logger.debug(f'Orcid response status code: {response.status_code}')
        logger.debug(f'Orcid response headers: {response.headers}')

        if response.status_code == 200:
            # Extract the JSON response
            json_data = response.json()

            # Check if the response contains any search results
            if 'result' in json_data and isinstance(json_data['result'], list) and json_data['result']:
                # Iterate through the first 10 results for now (can be changed)
                for result in json_data['result'][:10]:  
                    orcid_id = result['orcid-identifier']['path']

                    # Generate the URL to the person's public profile in ORCID
                    profile_url = f"https://orcid.org/{orcid_id}"

                    # Retrieve the public data for the found ORCID iD
                    public_data_url = f'https://pub.orcid.org/v3.0/{orcid_id}/person'
                    response = requests.get(public_data_url, headers=headers)

                    if response.status_code == 200:
                        # Extract the JSON response
                        json_data = response.json()
                        
                        # Extract the name information
                        name_data = json_data.get('name', {})
                        given_names = name_data.get('given-names', {}).get('value', '')

                        # Handling attribute error for 'NotType' when searching for none author search terms
                        family_name = ''
                        if 'family-name' in name_data and name_data['family-name'] is not None:
                            family_name = name_data.get('family-name', {}).get('value')

                        full_names = f"{given_names} {family_name}"

                        try:
                            display_name = name_data.get('credit-name', {}).get('value') or name_data.get('display-name', {}).get('value')
                        except AttributeError:
                            display_name = f"{given_names}{family_name}"

                        # Extract email information
                        email = json_data.get('emails', {}).get('email', [])
                        email = email[0]['email'] if email else None

                        researcher_urls = json_data.get('researcher-urls', {}).get('researcher-url', [])
                        keywords = json_data.get('keywords', {}).get('keyword', [])
                        external_identifiers = json_data.get('external-identifiers', {}).get('external-identifier', [])

                        researcher_url = [researcher_url.get('url', '') for researcher_url in researcher_urls]

                        keyword = [keyword.get('content', '') for keyword in keywords]

                        external_identifier_values = []
                        for external_identifier in external_identifiers:
                            external_identifier_type = external_identifier.get('external-id-type', '')
                            external_identifier_value = external_identifier.get('external-id-value', '')
                            external_identifier_values.append((external_identifier_type, external_identifier_value))
                        
                        affiliations = json_data.get('employments', {}).get('employment-summary', [])
                        if affiliations:
                            for affiliation in affiliations:
                                organization = affiliation.get('organization', {})
                                name = organization.get('name', '')
                                address = organization.get('address', {})
                                city = address.get('city', '')
                                region = address.get('region', '')
                                country = address.get('country', '')
                                # Assign the affiliation data to the affiliation_data dictionary
                                affiliation_data = {
                                    'name': name,
                                    'address': f"{city}, {region}, {country}"
                                }
                                results.append(
                                    Person(
                                        url=profile_url,
                                        name=full_names,
                                        affiliation=affiliation_data
                                    )
                                )
                        else:
                            affiliation_data = 'No affiliations found.'

                        results.append(
                            Person(
                                url=profile_url,
                                name=full_names,
                                affiliation=affiliation_data
                            )
                        )

                    else:
                        print("Failed to retrieve public data:", response.text)
            else:
                print("No results found for the search term:", search_term)
        else:
            print("Failed to search for public data:", response.text)

        logger.info(f'Got {len(results)} records from Orcid') 
        
    except requests.exceptions.RequestException as e:
        print("An error occurred during the request:", str(e))