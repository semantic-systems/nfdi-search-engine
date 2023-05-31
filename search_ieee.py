import requests
import logging
from objects import Ieee

logger = logging.getLogger('nfdi_search_engine')

def ieee(search_term, results):
    api_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
    api_key = "API_KEY"

    params = {
        "apikey": api_key,
        "querytext": search_term
    }

    try:
        # response = requests.get(api_url, params=params)
        # response.raise_for_status()
        # data = response.json()

        #This data is only for testing purposes as a sample. It will be replaced once the IEEE API key is activated 
        data = {
            "articles": [
                {
                    "title": "[Sample article] An Overview of Search Engine Optimization",
                    "authors": [
                        {
                            "full_name": "Varsha; P.S. Grover; Laxmi Ahuja"
                        }
                    ],
                    "doi": "https://ieeexplore.ieee.org/document/9596287",
                    "datepublished": "2021"
                    
                }
            ]
        }
        for article in data["articles"]:
            title = article["title"]
            authors = ", ".join(author["full_name"] for author in article["authors"])
            doi = article["doi"]
            date=article["datepublished"]
            
            # print(data)
            results.append(
                Ieee(
                    title=title,
                    url=doi,
                    authors=authors,
                    date=date
                )
            )
            
            logger.info(f"Got {len(results)} Researchers and scholarly articles from IEEE")

    except requests.exceptions.RequestException as e:
        print("Error occurred:", e)
