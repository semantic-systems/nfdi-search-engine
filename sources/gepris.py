import requests
from objects import Gepris
import logging
from bs4 import BeautifulSoup
from objects import Project, Person, Organization, Place
import utils

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    try:
        
        # function call to retrive author or researchers from GEPRIS
        find_author(search_term, results)
        # function call to retrive organizations or institutions from GEPRIS
        find_organization(search_term, results)

        base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
        url = f"{base_url}?context=projekt&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
    
        # response = requests.get(url)
        response = requests.get(url, timeout=3)
        response.raise_for_status()  # Raise an exception for non-2xx status codes

        logger.debug(f'Gepris response status code: {response.status_code}')
        logger.debug(f'Gepris response headers: {response.headers}')
    
        soup = BeautifulSoup(response.content, 'html.parser')
        result = soup.find("span", id="result-info")

        total_reocrds = result.text
        logger.info(f'GEPRIS - {total_reocrds} records found')
        
        if result:
            url = f"{base_url}?context=projekt&hitsPerPage={result.text}&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
            # response = requests.get(url)
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.content, 'html.parser')
        projects = soup.find("div", id="liste")
        
        if projects:
            entries = projects.find_all("div", class_=["eintrag_alternate","eintrag"])
            
            for entry in entries:
                try:
                    fundings = Project()
                    fundings.source = 'GEPRIS'
                    project_link = entry.find("a")["href"]
                    project_description = ''.join(entry.find("div", class_="beschreibung").find_all(string=True, recursive=False)).strip()
                    fundings.description = project_description
                    fundings.abstract = project_description
                    title = entry.find("h2").text.strip()
                    fundings.name = title
                    term = entry.find("div", class_="two_columns").find("span", class_="value2").text.strip()
                    fundings.dateLastModified = term
                    project_url = 'https://gepris.dfg.de' + project_link + '?language=en'
                    fundings.url = project_url
                    applicants_element = entry.find("div", class_="details").find("span", class_="value")
                    applicant_names = applicants_element.text.strip()
                    #check if there is more than one applicant 
                    if "," in applicant_names:
                        # If there are comma-separated names, split them and add each one to the fundings.author list
                        applicant_names_list = applicant_names.split(',')
                        for applicant_name in applicant_names_list:
                            author = Person()
                            author.type = "Person"
                            author.name = applicant_name.strip()
                            fundings.author.append(author)
                    else:
                        # If there is a single applicant, add it to the fundings.author list
                        author = Person()
                        author.type = "Person"
                        author.name = applicant_names
                        fundings.author.append(author)

                    
                    results['fundings'].append(fundings)

                except KeyError:
                    logger.warning("Key 'href' not found in 'a' tag. Skipping project.")
                # except AttributeError:
                #     logger.warning("Unable to find project details. Skipping project.")
        
        # logger.info(f'Got {len(results)} records from Gepris')
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')



def find_author(search_term, results):
    try:
        base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
        url = f"{base_url}?context=person&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
        
        try:
            
            response = requests.get(url, timeout=3)
            response.raise_for_status()  # Raise an exception for non-2xx status codes

            logger.debug(f'Gepris response status code: {response.status_code}')
            logger.debug(f'Gepris response headers: {response.headers}')
        
            soup = BeautifulSoup(response.content, 'html.parser')
            result = soup.find("span", id="result-info")

            total_reocrds = result.text
            logger.info(f'GEPRIS - {total_reocrds} records found')
            
            if result:
                url = f"{base_url}?context=person&hitsPerPage={result.text}&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"

                response = requests.get(url)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.content, 'html.parser')
            aurhtors_element = soup.find("div", id="liste")
            
            if aurhtors_element:
                authors = aurhtors_element.find_all("div", class_=["eintrag_alternate","eintrag"])
                
                for author in authors:
                    try:
                        authorObj = Person()
                        authorObj.source = 'GEPRIS'
                        authorObj.identifier = author.find("a")["href"]
                        authorObj.url = f'https://gepris.dfg.de{authorObj.identifier}'
                        author_names = author.find("h2").text.strip()
                        if "," in author_names:
                            authorObj.name = author_names.replace(",", " ")

                        authorObj.affiliation = ' '.join(author.find("div", class_="beschreibung").find_all(string=True, recursive=False)).strip()

                        results['researchers'].append(authorObj)

                    except KeyError:
                        logger.warning("Key 'href' not found in 'a' tag. Skipping project.")
                    except AttributeError:
                        logger.warning("Unable to find author for the search term")
            
            # logger.info(f'Got {len(results)} records from Gepris')
        
        except requests.exceptions.RequestException as e:
            logger.error(f'Error occurred while making a request to Gepris authors: {e}')
        except Exception as e:
            logger.error(f'An error occurred during the search: {e}')
        # except requests.exceptions.Timeout as ex:
        #     logger.error(f'Timed out Exception: {str(ex)}')
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')


def find_organization(search_term, results):
    try:

        base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
        url = f"{base_url}?context=institution&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
        
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()  # Raise an exception for non-2xx status codes

            logger.debug(f'Gepris response status code: {response.status_code}')
            logger.debug(f'Gepris response headers: {response.headers}')
        
            soup = BeautifulSoup(response.content, 'html.parser')
            result = soup.find("span", id="result-info")

            total_reocrds = result.text
            logger.info(f'GEPRIS - {total_reocrds} records found')
            
            if result:
                url = f"{base_url}?context=institution&hitsPerPage={result.text}&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"

                response = requests.get(url)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.content, 'html.parser')
            organization_list = soup.find("div", id="liste")
            try:
                if organization_list:
                    organizations = organization_list.find_all("div", class_=["eintrag_alternate","eintrag"])
                    
                    for organization in organizations:
                        try:

                            orgObj = Organization()
                            orgObj.source = 'GEPRIS'
                            id_link = organization.find("a")["href"]
                            id = id_link.split("/")[-1]
                            orgObj.identifier = id
                            orgObj.url = f'https://gepris.dfg.de/gepris/institution/{id}'
                            orgObj.name = organization.find("h2").text.strip()
                            # Find the organizations address and retrieve text after <br> tag
                            sub_organization = organization.find("div", class_="subInstitution")
                            if sub_organization:
                                orgObj.address = ','.join(sub_organization.find_all("br")[0].find_next_siblings(string=True)).strip()
                            else:
                                orgObj.address = " "

                            results['organizations'].append(orgObj)
                        except Exception as e:
                            logger.warning(e)
            except KeyError:
                logger.warning("Key not found.")
            except AttributeError:
                logger.warning("Unable to find organization details")

            # logger.info(f'Got {len(results)} records from Gepris')
        
        except requests.exceptions.RequestException as e:
            logger.error(f'Error occurred while making a request to Gepris institutions: {e}')
        except Exception as e:
            logger.error(f'An error occurred during the search: {e}')
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')


def org_details(organization_id, organization_name):
    try:       
        orgObj = Place()
        # URL for fetching organization details
        url_address_details = f'https://gepris.dfg.de/gepris/institution/{organization_id}?context=institution&task=showDetail&id={organization_id}'
        
        # Send an HTTP GET request to retrieve the organization details
        response = requests.get(url_address_details)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        if response.status_code == 200:
            # Parse the HTML response content
            soup = BeautifulSoup(response.content, 'html.parser')
            address_data = soup.find("div", id="address_data")

            if address_data:
                orgObj.source = 'GEPRIS'
                orgObj.name = organization_name
                address_span = address_data.find("span", class_="value")
                
                if address_span:
                    # Extract and format the organization's address
                    orgObj.address = '\n'.join([line.strip() for line in address_span.stripped_strings])
                    orgObj.identifier = organization_id

                    # Example usage:
                    # address = 'Vogt-Kölln-Straße 30 22527 Hamburg'
                    try:
                        coordinates = geocode_address(orgObj.address)
                        if coordinates:
                            latitude, longitude = coordinates
                            orgObj.latitude = latitude
                            orgObj.longitude = longitude
                            print(f'Latitude: {latitude}, Longitude: {longitude}')
                        else:
                            print('Address not found.')
                    except Exception as e:
                        print(f'An error occurred: {e}')

                    # print("org ID is =", organization_id)
                    # print("org Address is =", orgObj.address)
                else:
                    orgObj.address = ""
            else:
                # Log an error message if address details are not found
                logger.error("Address details not found.") 
        else:
            # Log an error message for unexpected HTTP status codes
            logger.error(f"Failed to retrieve data. Status code: {response.status_code}")
        
        return orgObj
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        # when timeout excepton is true "GEPRIS" will be returned
        return 'GEPRIS'
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')


import requests

def geocode_address(address):
    try:
        # Make a GET request to the Nominatim API
        url = f'https://nominatim.openstreetmap.org/search?format=json&q={address}'
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Check if the response contains results
            if data:
                # Extract latitude and longitude from the first result
                latitude = data[0]['lat']
                longitude = data[0]['lon']
                return latitude, longitude  # Return the latitude and longitude
            else:
                return None  # Address not found
        else:
            raise Exception(f'Error: {response.status_code}')
    except requests.exceptions.RequestException as req_err:
        # Handle errors related to the HTTP request (e.g., network issues)
        raise Exception(f'An error occurred during the HTTP request: {req_err}')
    except Exception as ex:
        # Handle any other unexpected errors
        raise Exception(f'An unexpected error occurred: {ex}')

