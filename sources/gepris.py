import requests
from objects import Gepris
import logging
from bs4 import BeautifulSoup
from objects import Project, Person, Organization
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
        results['timedout_sources'].append('GEPRIS')
        
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
                            orgObj.identifier = organization.find("a")["href"]
                            orgObj.url = f'https://gepris.dfg.de{orgObj.identifier}'
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
        results['timedout_sources'].append('GEPRIS')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')