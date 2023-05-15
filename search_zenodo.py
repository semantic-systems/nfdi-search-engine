import requests
from objects import Zenodo
import logging
import os

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


def zenodo(search_term, results):
    response = requests.get('https://zenodo.org/api/records',
                            params={'q': search_term,
                                    'access_token': 'rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL'})

    logger.debug(f'Zenodo response status code: {response.status_code}')
    logger.debug(f'Zenodo response headers: {response.headers}')

    for data in response.json()['hits']['hits']:
        if 'conceptdoi' in data:
            # TODO Align and extend with schema.org concepts
            # resource = _make_zenodo_uri(data)
            # resource_type = URIRef('zenodo:' + data['metadata']['resource_type']['type'])
            resource_type = 'zenodo:' + data['metadata']['resource_type']['type']
            authors_list = '; '.join([authors["name"] for authors in data['metadata']['creators']])
            results.append(
                Zenodo(
                    resource_type=resource_type,
                    url=data["links"]["doi"],
                    date=data['metadata']['publication_date'],
                    title=data['metadata']['title'],
                    author=authors_list
                )
            )
    logger.info(f'Got {len(results)} records from Zenodo')
    # return results
    # logger.info(f"Graph g has {len(g)} statements after querying Zenodo.")
