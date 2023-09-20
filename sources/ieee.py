import requests
import logging
import utils
from objects import Article, Person

logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term, results):
    try:
        
        # API key and 
        api_key = '4nm2vdr778weget78v9ubgdb'
        # maximum number of records to retrieve, it's changable
        max_records = 100

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'nfdi4dsBot/1.0 (https://www.nfdi4datascience.de/nfdi4dsBot/; nfdi4dsBot@nfdi4datascience.de)'
        }

        # search URL with the provided search term, API key, and max records
        search_url = f'http://ieeexploreapi.ieee.org/api/v1/search/articles?querytext={search_term}&apikey={api_key}&max_records={max_records}'

        try:
            # Send GET request to the search URL
            # response = requests.get(search_url, headers=headers)
            response = requests.get(search_url, timeout=3)


            # Logging the response details
            logger.debug(f'Ieee response status code: {response.status_code}')
            logger.debug(f'Ieee response headers: {response.headers}')

            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                # Extract the JSON response
                data = response.json()
                total_records = data.get("total_records", "")
                
                logger.info(f'IEEE - {total_records} records found')

                # Check if there are any articles found
                if 'articles' in data:
                    articles = data['articles']
                    for article in articles:
                        publication = Article()
                        publication.source = 'IEEE'
                        # Extract article information from the JSON response
                        publication.name = article.get('title', '')
                        description = article.get('abstract', '')
                        publication.abstract = utils.remove_html_tags(description)
                        publication.description = utils.remove_html_tags(description)
                        publication.datePublished = article.get('publication_date', '')
                        publication.url = article.get('html_url', '')
                        publication.publisher = article.get('publisher', '')
                        publication.pageStart = article.get('start_page', '')
                        publication.pageEnd = article.get('end_page', '')
                        publication.citation = article.get('citing_paper_count', '')
                        keywords = article.get("keywords", '')
                        if keywords:
                            for keyword in keywords:
                                publication.keywords.append(keyword)

                        languages = article.get("inLanguage", None)
                        if languages:
                            for language in languages:
                                publication.inLanguage.append(language)
    
                        for author_data in article.get('authors', {}).get('authors', []):
                            author = Person()
                            author.type = "Person"
                            author.name = author_data.get("full_name", "")
                            author.identifier = author_data.get("id", "")
                            publication.author.append(author)


                        results['publications'].append(publication)

                else:
                    print("No results found for the search term:", search_term)
            else:
                print("Failed to retrieve the data:", response.text)

            # Logging the number of records retrieved from Ieee
            # logger.info(f'Got {len(results)} records from Ieee')

        except requests.exceptions.RequestException as e:
            logger.error("An error occurred during the request:", str(e))
        except KeyError as ke:
            logger.error("Key not found:", str(ke))
        except ValueError as ve:
            logger.error("Invalid JSON response:", str(ve))
        # except Exception as ex:
        #     print("An unexpected error occurred:", str(ex))
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')