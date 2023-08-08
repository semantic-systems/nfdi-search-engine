import requests
from objects import Gepris
import logging
from bs4 import BeautifulSoup
from objects import Project, Person
import utils

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    # function call to retrive author or researchers from GEPRIS
    find_authors(search_term, results)

    base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
    url = f"{base_url}?context=projekt&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for non-2xx status codes

        logger.debug(f'Gepris response status code: {response.status_code}')
        logger.debug(f'Gepris response headers: {response.headers}')
    
        soup = BeautifulSoup(response.content, 'html.parser')
        result = soup.find("span", id="result-info")

        total_reocrds = result.text
        logger.info(f'GEPRIS - {total_reocrds} records found')
        
        if result:
            url = f"{base_url}?context=projekt&hitsPerPage={result.text}&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
            response = requests.get(url)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.content, 'html.parser')
        projects = soup.find("div", id="liste")
        
        if projects:
            entries = projects.find_all("div", class_=["eintrag_alternate","eintrag"])
            
            for entry in entries:
                try:
                    resources = Project()
                    resources.source = 'GEPRIS'
                    project_link = entry.find("a")["href"]
                    project_description = ''.join(entry.find("div", class_="beschreibung").find_all(string=True, recursive=False)).strip()
                    resources.description = project_description
                    resources.abstract = project_description
                    title = entry.find("h2").text.strip()
                    resources.name = title
                    term = entry.find("div", class_="two_columns").find("span", class_="value2").text.strip()
                    resources.dateLastModified = term
                    project_url = 'https://gepris.dfg.de' + project_link + '?language=en'
                    resources.url = project_url
                    applicants_element = entry.find("div", class_="details").find("span", class_="value")
                    applicant_names = applicants_element.text.strip()
                    #check if it's more than one applicant 
                    if "," in applicant_names:
                        # If there are comma-separated names, split them and add each one to the resources.author list
                        applicant_names_list = applicant_names.split(',')
                        for applicant_name in applicant_names_list:
                            author = Person()
                            author.type = "Person"
                            author.name = applicant_name.strip()
                            resources.author.append(author)
                    else:
                        # If there is a single applicant, add it to the resources.author list
                        author = Person()
                        author.type = "Person"
                        author.name = applicant_names
                        resources.author.append(author)

                    
                    results['resources'].append(resources)

                except KeyError:
                    logger.warning("Key 'href' not found in 'a' tag. Skipping project.")
                except AttributeError:
                    logger.warning("Unable to find project details. Skipping project.")
        
        logger.info(f'Got {len(results)} records from Gepris')
    
    except requests.exceptions.RequestException as e:
        logger.error(f'Error occurred while making a request to Gepris: {e}')
    except Exception as e:
        logger.error(f'An error occurred during the search: {e}')


def find_authors(search_term, results):

    base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
    url = f"{base_url}?context=person&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
    
    try:
        response = requests.get(url)
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
                    logger.warning("Unable to find project details. Skipping project.")
        
        # logger.info(f'Got {len(results)} records from Gepris')
    
    except requests.exceptions.RequestException as e:
        logger.error(f'Error occurred while making a request to Gepris: {e}')
    except Exception as e:
        logger.error(f'An error occurred during the search: {e}')