import requests
import logging
import utils
from objects import thing, Article, Author
from sources import data_retriever
import traceback

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term: str, results):
    source = "ORKG"
    details_api = "https://orkg.org/api/"
    author_url = "https://orkg.org/author/"

    try:
        search_result = data_retriever.retrieve_data(source=source,
                                                     base_url=utils.config["search_url_orkg"],
                                                     search_term=search_term,
                                                     results=results)

        total_hits = search_result['totalElements']
        logger.info(f'{source} - {total_hits} records matched; pulled top {total_hits}')

        hits = search_result['content']
        for hit in hits:
            id = hit.get('id', None)
            classes = hit.get('classes', [])
            if 'Paper' in classes:
                api_url = details_api + 'papers/' + id
                response = requests.get(api_url)
                paper = response.json()
                publication = Article()
                _source = thing()
                _source.name = source
                publication.source.append(_source)
                publication.name = paper.get('title', '')
                publication.url = api_url
                publication.identifier = paper.get('identifiers', {}).get('doi', '')
                month = paper.get('publication_info', {}).get('published_month', None)
                year = paper.get('publication_info', {}).get('published_year', None)
                if month is not None and year is not None:
                    publication.datePublished = str(month) + '/' + str(year)
                elif year is not None:
                    publication.datePublished = str(year)

                if paper.get('authors', []):
                    for item in paper.get('authors', []):
                        author = Author()
                        author.type = 'Person'
                        author.name = item.get('name', '')
                        author.identifier = item.get('identifiers', {}).get('orcid', '')
                        if item.get('id', ''):
                            author.url = author_url + item.get('id')
                        publication.author.append(author)
                results['publications'].append(publication)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())
