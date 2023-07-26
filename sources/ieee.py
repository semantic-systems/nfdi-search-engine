import requests
import logging
import utils
from objects import Article

logger = logging.getLogger('nfdi_search_engine')


def search(search_term, results):
    # API key and 
    api_key = '4nm2vdr778weget78v9ubgdb'
    # maximum number of records to retrieve, it's changable
    max_records = 1000

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'nfdi4dsBot/1.0 (https://www.nfdi4datascience.de/nfdi4dsBot/; nfdi4dsBot@nfdi4datascience.de)'
    }

    # search URL with the provided search term, API key, and max records
    search_url = f'http://ieeexploreapi.ieee.org/api/v1/search/articles?querytext={search_term}&apikey={api_key}&max_records={max_records}'

    try:
        # Send GET request to the search URL
        response = requests.get(search_url, headers=headers)

        # Logging the response details
        logger.debug(f'Ieee response status code: {response.status_code}')
        logger.debug(f'Ieee response headers: {response.headers}')

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Extract the JSON response
            data = response.json()

            # Check if there are any articles found
            if 'articles' in data:
                articles = data['articles']
                for article in articles:
                    # Extract article information from the JSON response
                    title = article.get('title', '')
                    description = article.get('abstract', '')
                    short_description = utils.remove_html_tags(description)
                    publication_date = article.get('publication_date', '')
                    url = article.get('html_url', '')

                    authors_list = ''
                    if 'authors' in article:
                        authors = article['authors']['authors']
                        # Concatenate authors' names with a comma separator
                        authors_list = ', '.join([author.get('full_name', '') for author in authors])

                    # Create an Article object and add it to the results list
                    results.append(
                        Article(
                            title=title,
                            url=url,
                            authors=authors_list,
                            description=short_description,
                            date=publication_date,
                        )
                    )

            else:
                print("No results found for the search term:", search_term)
        else:
            print("Failed to retrieve the data:", response.text)

        # Logging the number of records retrieved from Ieee
        logger.info(f'Got {len(results)} records from Ieee')

    except requests.exceptions.RequestException as e:
        print("An error occurred during the request:", str(e))
    except KeyError as ke:
        print("Key not found:", str(ke))
    except ValueError as ve:
        print("Invalid JSON response:", str(ve))
    except Exception as ex:
        print("An unexpected error occurred:", str(ex))