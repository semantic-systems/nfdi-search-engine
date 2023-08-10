import requests
import utils
from objects import Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Person
import logging
import os

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


def search(search_term, results):
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
            # zenodo_resource_type = 'zenodo:' + data['metadata']['resource_type']['type']
            resource_type = data['metadata']['resource_type']['type']
            # authors_list = '; '.join([authors["name"] for authors in data['metadata']['creators']]
            description_txt = data["metadata"]["description"]
            description = utils.remove_html_tags(description_txt)
            if resource_type == 'publication':
                publication = Article()
                publication.source = 'Zenodo'
                publication.name = data['metadata']['title']
                publication.url = data["links"]["doi"]
                publication.image = ''
                publication.description = description
                publication.abstract = ''
                keywords = data['metadata'].get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        for key in keyword.split(","):
                            publication.keywords.append(key)
                elif isinstance(keywords, dict):
                    for keyword in keywords.get('buckets', []):
                        for items in keyword:
                            publication.keywords.append(items['key'])
                else:
                    publication.keywords.append('')
                language = ''
                if 'language' in data['metadata']:
                    language = data['metadata']['language']
                publication.inLanguage.append(language)
                publication.datePublished = data['metadata']['publication_date']
                publication.license = data['metadata']['license']['id']
                for authors in data['metadata']['creators']:
                    author = Person()
                    author.name = authors["name"]
                    author.type = 'Person'
                    author.affiliation = ''
                    if 'affiliation' in authors:
                        author.affiliation = authors['affiliation']
                    author.identifier = ''
                    if 'orcid' in authors:
                        author.identifier = authors['orcid']
                    publication.author.append(author)

                results['publications'].append(publication)
                '''
                results.append(
                    Article(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        description=description,
                        authors=authors_list
                    )
                )
            elif resource_type == 'presentation':
                results.append(
                    Presentation(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        description=description,
                        authors=authors_list
                    )
                )
            elif resource_type == 'poster':
                results.append(
                    Poster(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        description=description,
                        authors=authors_list
                    )
                )
            elif resource_type == 'dataset':
                results.append(
                    Dataset(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        description=description,
                        authors=authors_list
                    )
                )
            elif resource_type == 'software':
                version = ''
                if 'version' in data['metadata']:
                    version = data['metadata']['version']
                results.append(
                    Software(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        description=description,
                        version=version,
                        authors=authors_list
                    )
                )
            elif resource_type == 'lesson':
                results.append(
                    Lesson(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        description=description,
                        authors=authors_list
                    )
                )
            elif resource_type == 'video':
                results.append(
                    Video(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        authors=authors_list
                    )
                )
            elif resource_type == 'image':
                results.append(
                    Image(
                        title=data['metadata']['title'],
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        authors=authors_list
                    )
                )
            else:
                results.append(
                    Zenodo(
                        resource_type=zenodo_resource_type,
                        url=data["links"]["doi"],
                        date=data['metadata']['publication_date'],
                        title=data['metadata']['title'],
                        description=description,
                        author=authors_list
                    )
                )
             '''

    logger.info(f'Got {len(results)} records from Zenodo')
