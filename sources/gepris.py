import requests
from objects import Gepris
import logging
from bs4 import BeautifulSoup
from objects import Project, Person, Organization, Place, Author, thing
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

        # base_url = utils.config["search_url_gepris"]
        # url = base_url + search_term

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
        results['timedout_sources'].append('GEPRIS')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')



def find_author(search_term, results):
    try:
        base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
        url = f"{base_url}?context=person&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
            
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
                    authorObj = Author()
                    authorObj.source.append(thing(name='GEPRIS', identifier=author.find("a")["href"], url=f'https://gepris.dfg.de{authorObj.identifier}'))
                    # authorObj.identifier = author.find("a")["href"]
                    # authorObj.url = f'https://gepris.dfg.de{authorObj.identifier}'
                    author_names = author.find("h2").text.strip()
                    if "," in author_names:
                        authorObj.name = author_names.replace(",", " ")

                    for inst in author.find("div", class_="beschreibung").find_all(string=True, recursive=False):
                        authorObj.affiliation.append(Organization(name=inst))
                    results['researchers'].append(authorObj)

                except KeyError:
                    logger.warning("Key 'href' not found in 'a' tag. Skipping project.")
                except AttributeError:
                    logger.warning("Unable to find author for the search term")
            
            # logger.info(f'Got {len(results)} records from Gepris')
    
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('GEPRIS')

    except requests.exceptions.RequestException as e:
        logger.error(f'Error occurred while making a request to Gepris authors: {e}')
           
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')


def find_organization(search_term, results):
    try:

        base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
        url = f"{base_url}?context=institution&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
        
        response = requests.get(url, timeout=3)
        response.raise_for_status()  # Raise an exception for non-2xx status codes

        logger.debug(f'Gepris response status code: {response.status_code}')
        logger.debug(f'Gepris response headers: {response.headers}')
    
        soup = BeautifulSoup(response.content, 'html.parser')
        result = soup.find("span", id="result-info")

        total_reocrds = result.text
        logger.info(f'GEPRIS - {total_reocrds} records found')
        
        # logger.info(f'Got {len(results)} records from Gepris')

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

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append('GEPRIS')        
    
    except requests.exceptions.RequestException as e:
        logger.error(f'Error occurred while making a request to Gepris institutions: {e}')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')


def org_details(organization_id, organization_name):
    try:       
        organization = Place()
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
                organization.source = 'GEPRIS'
                organization.name = organization_name
                address_span = address_data.find("span", class_="value")
                
                if address_span:
                    # Extract and format the organization's address
                    organization.address = '\n'.join([line.strip() for line in address_span.stripped_strings])
                    organization.identifier = organization_id

                    # Example usage:
                    # address = 'Vogt-Kölln-Straße 30 22527 Hamburg'
                    try:
                        coordinates = geocode_address(organization.address)
                        if coordinates:
                            latitude, longitude, place_id, place_rank, place_type, address_type, licence = coordinates
                            organization.latitude = latitude
                            organization.longitude = longitude
                            organization.identifier = place_id
                            organization.aggregateRating = place_rank
                            organization.placType = place_type
                            organization.addressType = address_type
                            organization.licence = licence
                        else:
                            logger.error('Latitude and Longitude are not available.')
                    except Exception as e:
                        logger.error(f'An error occurred: {e}')
                else:
                    organization.address = ""

                # an empty list for sub_organizations
                sub_organizations_list = []
                sub_organizations = soup.find("div", id="untergeordneteInstitutionen")

                if sub_organizations:
                    for sub_organization in sub_organizations.find_all("li"):
                        sub_org = Organization()
                        sub_org.source = 'GEPRIS'
                        sub_org.identifier = sub_organization.get("id")
                        sub_org.url = 'https://gepris.dfg.de/gepris/institution/' + sub_org.identifier
                        sub_org.name = sub_organization.find("a").text.strip()
                        sub_organizations_list.append(sub_org)    
                else:
                    logger.error("Sub organizations not available.")

                # an empty list for sub_projects
                sub_projects_list = []
                sub_project = soup.find("div", id="beteiligungen-main")
                if sub_project:
                    for sub_proj in sub_project.find_all("a", class_=["intern", "hrefWithNewLine"]):
                        sub_project = Project()
                        if "intern" in sub_proj.get("class", []) and "hrefWithNewLine" in sub_proj.get("class", []):
                            sub_project_link_id = sub_proj["href"]
                            sub_project.identifier = sub_project_link_id.split("/")[-1]
                            sub_project.url = 'https://gepris.dfg.de/gepris/projekt/' + sub_project.identifier
                            sub_project.name = sub_proj.text.strip()
                            sub_projects_list.append(sub_project)
                            
                else:
                    logger.error("Sub projects not available.")
            else:
                # Log an error message if address details are not found
                logger.error("Address details not found.") 
        else:
            # Log an error message for unexpected HTTP status codes
            logger.error(f"Failed to retrieve data. Status code: {response.status_code}")
        
        return organization, sub_organizations_list, sub_projects_list
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        # when timeout excepton is true "GEPRIS" will be returned
        return 'GEPRIS'
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')


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
                #Extract attributes from the first result
                first_result = data[0]
                latitude = first_result.get('lat', 'none')
                longitude = first_result.get('lon', 'none')
                place_id = first_result.get('place_id', 'none')
                place_rank = first_result.get('place_rank','none')
                place_type = first_result.get('type', 'none')
                address_type = first_result.get('addresstype', 'none')
                licence = first_result.get('licence', 'none')

                return latitude, longitude, place_id, place_rank, place_type, address_type, licence  # Return the attributes
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