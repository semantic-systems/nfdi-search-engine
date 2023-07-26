import requests
from objects import Gepris
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger('nfdi_search_engine')


def search(search_term, results):
    base_url = 'https://gepris.dfg.de/gepris/OCTOPUS'
    url = f"{base_url}?context=projekt&hitsPerPage=1&index=0&keywords_criterion={search_term}&language=en&task=doSearchSimple"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
    
        soup = BeautifulSoup(response.content, 'html.parser')
        result = soup.find("span", id="result-info")
        
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
                    project_link = entry.find("a")["href"]
                    project_description = ''.join(entry.find("div", class_="beschreibung").find_all(text=True, recursive=False)).strip()
                    title = entry.find("h2").text.strip()
                    term = entry.find("div", class_="two_columns").find("span", class_="value2").text.strip()
                    applicant_leader = entry.find("div", class_="details").find("span", class_="value").text.strip()
                    
                    project_url = 'https://gepris.dfg.de' + project_link + '?language=en'
                    
                    results.append(
                        Gepris(
                            url=project_url,
                            title=title,
                            description=project_description,
                            date=term,
                            applicant_or_leader=applicant_leader
                        )
                    )
                except KeyError:
                    logger.warning("Key 'href' not found in 'a' tag. Skipping project.")
                except AttributeError:
                    logger.warning("Unable to find project details. Skipping project.")
        
        logger.info(f'Got {len(results)} records from Gepris')
    
    except requests.exceptions.RequestException as e:
        logger.error(f'Error occurred while making a request to Gepris: {e}')
    except Exception as e:
        logger.error(f'An error occurred during the search: {e}')