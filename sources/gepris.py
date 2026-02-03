from objects import Project, Person, Organization, Place, Author, thing
from sources.base import BaseSource
from typing import Iterable, Dict, Any
import requests
from bs4 import BeautifulSoup
import logging
import re
import utils
from main import app

logger = logging.getLogger('nfdi_search_engine')


class GEPRIS(BaseSource):
    """
    GEPRIS source implementation for searching projects, researchers, and organizations.
    """

    SOURCE = "gepris"

    @utils.handle_exceptions
    def fetch(self, search_term: str, context: str = 'projekt', failed_sources: list = None) -> Dict[str, Any]:
        """
        Fetch raw HTML from GEPRIS using the given search term and context.
        
        Args:
            search_term: The search term to query
            context: The context type ('projekt', 'person', or 'institution')
            failed_sources: List to append source name if request fails
            
        Returns:
            Dictionary containing the HTML response and metadata
        """
        endpoint = app.config["DATA_SOURCES"][self.SOURCE].get("search-endpoint", "")
        base_url = endpoint.split("?")[0] if "?" in endpoint else endpoint
        # First request to get total count
        url = f"{base_url}?context={context}&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
        
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            result = soup.find("span", id="result-info")
            
            if not result:
                logger.info(f'{self.SOURCE} - No results found for {context}')
                return {'html': None, 'total_available': 0, 'context': context}
            
            total_records_text = result.text.strip()
            logger.info(f'{self.SOURCE} - {total_records_text} records found for {context}')
            
            # Extract number from result text
            max_records = app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']
            numbers = re.findall(r'\d+', total_records_text)
            if numbers:
                total_available = int(numbers[-1])
                hits_per_page = min(max_records, total_available)
            else:
                hits_per_page = max_records
                total_available = 0
            
            # Second request to get actual results
            url = f"{base_url}?context={context}&hitsPerPage={hits_per_page}&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return {
                'html': response.content,
                'total_available': total_available,
                'context': context
            }
            
        except requests.exceptions.Timeout as ex:
            logger.error(f'{self.SOURCE} - Timed out Exception: {str(ex)}')
            if failed_sources is not None:
                failed_sources.append(self.SOURCE)
            return {'html': None, 'total_available': 0, 'context': context}
        except Exception as ex:
            logger.error(f'{self.SOURCE} - Exception: {str(ex)}')
            if failed_sources is not None:
                failed_sources.append(self.SOURCE)
            return {'html': None, 'total_available': 0, 'context': context}

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw HTML response.
        
        Args:
            raw: Dictionary containing HTML content and metadata
            
        Returns:
            Iterable of BeautifulSoup elements representing hits
        """
        if not raw.get('html'):
            return []
        
        soup = BeautifulSoup(raw['html'], 'html.parser')
        projects = soup.find("div", id="liste")
        
        if projects:
            entries = projects.find_all("div", class_=["eintrag_alternate", "eintrag"])
            logger.info(f'{self.SOURCE} - Got {len(entries)} {raw["context"]} records')
            return entries
        else:
            logger.info(f'{self.SOURCE} - No {raw["context"]} found in results')
            return []

    @utils.handle_exceptions
    def map_hit(self, source_name: str, hit: Dict[str, Any]):
        """
        Map a single hit from GEPRIS to a Project object.
        
        Args:
            source_name: Name of the source (unused, kept for interface compatibility)
            hit: BeautifulSoup element representing a project entry
            
        Returns:
            Project object or None if mapping fails
        """
        try:
            project = Project()
            project_link = hit.find("a")["href"]
            project_identifier = project_link.split("/")[-1] if "/" in project_link else project_link
            
            # Create source thing object
            _source = thing()
            _source.name = app.config["DATA_SOURCES"][self.SOURCE]["logo"]["name"]
            _source.identifier = project_identifier
            project_url = 'https://gepris.dfg.de' + project_link + '?language=en'
            _source.url = project_url
            project.source.append(_source)
            
            project_description = ''.join(hit.find("div", class_="beschreibung").find_all(string=True, recursive=False)).strip()
            project.description = project_description
            project.abstract = project_description
            title = hit.find("h2").text.strip()
            project.name = title
            
            # Try to get date modified, but don't fail if it doesn't exist
            try:
                term = hit.find("div", class_="two_columns").find("span", class_="value2").text.strip()
                project.dateModified = term
            except (AttributeError, KeyError):
                pass  # dateModified is optional
            
            project.url = project_url
            
            # Try to get applicants, but don't fail if it doesn't exist
            try:
                applicants_element = hit.find("div", class_="details").find("span", class_="value")
                applicant_names = applicants_element.text.strip()
                # Check if there is more than one applicant
                if "," in applicant_names:
                    # If there are comma-separated names, split them and add each one to the project.author list
                    applicant_names_list = applicant_names.split(',')
                    for applicant_name in applicant_names_list:
                        author = Person()
                        author.additionalType = "Person"
                        author.name = applicant_name.strip()
                        project.author.append(author)
                else:
                    # If there is a single applicant, add it to the project.author list
                    author = Person()
                    author.additionalType = "Person"
                    author.name = applicant_names
                    project.author.append(author)
            except (AttributeError, KeyError):
                pass  # authors are optional
            
            return project
            
        except KeyError as e:
            logger.warning(f"{self.SOURCE} - Key error while processing project: {e}. Skipping project.")
            return None
        except AttributeError as e:
            logger.warning(f"{self.SOURCE} - Attribute error while processing project: {e}. Skipping project.")
            return None
        except Exception as e:
            logger.warning(f"{self.SOURCE} - Error while processing project: {e}. Skipping project.")
            return None

    @utils.handle_exceptions
    def fetch_researchers(self, search_term: str, failed_sources: list = None) -> Dict[str, Any]:
        """
        Fetch researchers/authors from GEPRIS.
        
        Args:
            search_term: The search term to query
            failed_sources: List to append source name if request fails
            
        Returns:
            Dictionary containing the HTML response and metadata
        """
        return self.fetch(search_term, context='person', failed_sources=failed_sources)

    @utils.handle_exceptions
    def extract_researcher_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract researcher hits from the raw HTML response.
        
        Args:
            raw: Dictionary containing HTML content and metadata
            
        Returns:
            Iterable of BeautifulSoup elements representing researcher entries
        """
        if not raw.get('html'):
            return []
        
        soup = BeautifulSoup(raw['html'], 'html.parser')
        authors_element = soup.find("div", id="liste")
        
        if authors_element:
            authors = authors_element.find_all("div", class_=["eintrag_alternate", "eintrag"])
            logger.info(f'{self.SOURCE} - Got {len(authors)} author records')
            return authors
        else:
            logger.info(f'{self.SOURCE} - No authors found in results')
            return []

    @utils.handle_exceptions
    def map_researcher_hit(self, hit: Dict[str, Any]) -> Author:
        """
        Map a single researcher hit to an Author object.
        
        Args:
            hit: BeautifulSoup element representing a researcher entry
            
        Returns:
            Author object or None if mapping fails
        """
        try:
            authorObj = Author()
            author_link = hit.find("a")["href"]
            author_identifier = author_link.split("/")[-1] if "/" in author_link else author_link
            
            _source = thing()
            _source.name = app.config["DATA_SOURCES"][self.SOURCE]["logo"]["name"]
            _source.identifier = author_identifier
            _source.url = f'https://gepris.dfg.de{author_link}'
            authorObj.source.append(_source)
            
            author_names = hit.find("h2").text.strip()
            if "," in author_names:
                authorObj.name = author_names.replace(",", " ")
            else:
                authorObj.name = author_names

            for inst in hit.find("div", class_="beschreibung").find_all(string=True, recursive=False):
                authorObj.affiliation.append(Organization(name=inst))
            
            return authorObj
            
        except KeyError:
            logger.warning(f"{self.SOURCE} - Key 'href' not found in 'a' tag. Skipping author.")
            return None
        except AttributeError:
            logger.warning(f"{self.SOURCE} - Unable to find author for the search term")
            return None
        except Exception as e:
            logger.warning(f"{self.SOURCE} - Error processing researcher: {e}")
            return None

    @utils.handle_exceptions
    def fetch_organizations(self, search_term: str, failed_sources: list = None) -> Dict[str, Any]:
        """
        Fetch organizations from GEPRIS.
        
        Args:
            search_term: The search term to query
            failed_sources: List to append source name if request fails
            
        Returns:
            Dictionary containing the HTML response and metadata
        """
        return self.fetch(search_term, context='institution', failed_sources=failed_sources)

    @utils.handle_exceptions
    def extract_organization_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract organization hits from the raw HTML response.
        
        Args:
            raw: Dictionary containing HTML content and metadata
            
        Returns:
            Iterable of BeautifulSoup elements representing organization entries
        """
        if not raw.get('html'):
            return []
        
        soup = BeautifulSoup(raw['html'], 'html.parser')
        organization_list = soup.find("div", id="liste")
        
        if organization_list:
            organizations = organization_list.find_all("div", class_=["eintrag_alternate", "eintrag"])
            logger.info(f'{self.SOURCE} - Got {len(organizations)} organization records')
            return organizations
        else:
            logger.info(f'{self.SOURCE} - No organizations found in results')
            return []

    @utils.handle_exceptions
    def map_organization_hit(self, hit: Dict[str, Any]) -> Organization:
        """
        Map a single organization hit to an Organization object.
        
        Args:
            hit: BeautifulSoup element representing an organization entry
            
        Returns:
            Organization object or None if mapping fails
        """
        try:
            orgObj = Organization()
            id_link = hit.find("a")["href"]
            org_id = id_link.split("/")[-1]
            orgObj.identifier = org_id
            orgObj.url = f'https://gepris.dfg.de/gepris/institution/{org_id}'
            
            # Create source thing object
            _source = thing()
            _source.name = app.config["DATA_SOURCES"][self.SOURCE]["logo"]["name"]
            _source.identifier = org_id
            _source.url = orgObj.url
            orgObj.source.append(_source)
            
            orgObj.name = hit.find("h2").text.strip()
            
            # Find the organization's address and retrieve text after <br> tag
            sub_organization = hit.find("div", class_="subInstitution")
            if sub_organization:
                orgObj.address = ','.join(sub_organization.find_all("br")[0].find_next_siblings(string=True)).strip()
            else:
                orgObj.address = " "
            
            return orgObj
            
        except KeyError:
            logger.warning(f"{self.SOURCE} - Key not found.")
            return None
        except AttributeError:
            logger.warning(f"{self.SOURCE} - Unable to find organization details")
            return None
        except Exception as e:
            logger.warning(f"{self.SOURCE} - Error processing organization: {e}")
            return None

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch data from GEPRIS for projects, researchers, and organizations,
        extract hits, map them to objects, and insert them in-place into the results dict.
        
        Args:
            source_name: Name of the source (unused, kept for interface compatibility)
            search_term: The search term to query
            results: Dictionary to store results in
            failed_sources: List to append source name if request fails
        """
        # Search for researchers/authors
        try:
            raw_researchers = self.fetch_researchers(search_term, failed_sources)
            researcher_hits = self.extract_researcher_hits(raw_researchers)
            for hit in researcher_hits:
                researcher = self.map_researcher_hit(hit)
                if researcher:
                    results['researchers'].append(researcher)
        except Exception as e:
            logger.error(f'{self.SOURCE} - Error searching researchers: {e}')

        # Search for organizations
        try:
            raw_organizations = self.fetch_organizations(search_term, failed_sources)
            organization_hits = self.extract_organization_hits(raw_organizations)
            for hit in organization_hits:
                organization = self.map_organization_hit(hit)
                if organization:
                    results['organizations'].append(organization)
        except Exception as e:
            logger.error(f'{self.SOURCE} - Error searching organizations: {e}')

        # Search for projects
        try:
            raw = self.fetch(search_term, context='projekt', failed_sources=failed_sources)
            hits = self.extract_hits(raw)
            
            for hit in hits:
                project = self.map_hit(source_name, hit)
                if project:
                    results['projects'].append(project)
        except Exception as e:
            logger.error(f'{self.SOURCE} - Error searching projects: {e}')


@utils.handle_exceptions
def org_details(organization_id, organization_name):
    """
    Fetch detailed information about an organization from GEPRIS.
    
    Args:
        organization_id: The GEPRIS identifier for the organization
        organization_name: The name of the organization
        
    Returns:
        Tuple of (organization Place object, sub_organizations_list, sub_projects_list)
        or 'GEPRIS' string on timeout/error
    """
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
        # when timeout exception is true "GEPRIS" will be returned
        return 'GEPRIS'
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        return None


@utils.handle_exceptions
def geocode_address(address):
    """
    Geocode an address using the Nominatim API.
    
    Args:
        address: The address string to geocode
        
    Returns:
        Tuple of (latitude, longitude, place_id, place_rank, place_type, address_type, licence)
        or None if address not found
    """
    try:
        # Make a GET request to the Nominatim API
        url = f'https://nominatim.openstreetmap.org/search?format=json&q={address}'
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Check if the response contains results
            if data:
                # Extract attributes from the first result
                first_result = data[0]
                latitude = first_result.get('lat', 'none')
                longitude = first_result.get('lon', 'none')
                place_id = first_result.get('place_id', 'none')
                place_rank = first_result.get('place_rank', 'none')
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


@utils.timeit
@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search GEPRIS for projects, researchers, and organizations.
    """
    GEPRIS().search(source, search_term, results, failed_sources)
