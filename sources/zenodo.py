import requests
import utils
from objects import Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Person, LearningResource, CreativeWork, VideoObject, ImageObject
import logging
import os

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
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
            resource_type = data.get('metadata', {}).get('resource_type', {}).get('type')
            # authors_list = '; '.join([authors["name"] for authors in data['metadata']['creators']]
            description_txt = data.get('metadata', {}).get('description')
            description = utils.remove_html_tags(description_txt)
            if resource_type == 'publication':
                publication = Article()
                publication.source = 'Zenodo'
                publication.name = data.get('metadata', {}).get('title', None)
                publication.url = data.get('links', {}).get('doi', None)
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
                publication.datePublished = data.get('metadata', {}).get('publication_date')
                publication.license = data.get('metadata', {}).get('license', {}).get('id')
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

            elif resource_type == 'presentation':
                ppt = LearningResource()
                ppt.source = 'Zenodo'
                ppt.name = data.get('metadata', {}).get('title', None)
                ppt.url = data.get('links', {}).get('doi', None)
                ppt.description = description
                ppt.datePublished = data.get('metadata', {}).get('publication_date')
                ppt.license = data.get('metadata', {}).get('license', {}).get('id')

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
                    ppt.author.append(author)

                language = ''
                if 'language' in data['metadata']:
                    language = data['metadata']['language']
                ppt.inLanguage.append(language)

                keywords = data['metadata'].get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        for key in keyword.split(","):
                            ppt.keywords.append(key)
                elif isinstance(keywords, dict):
                    for keyword in keywords.get('buckets', []):
                        for items in keyword:
                            ppt.keywords.append(items['key'])
                else:
                    ppt.keywords.append('')

                results['resources'].append(ppt)
            
            elif resource_type == 'poster':
                poster = CreativeWork()
                poster.source = 'Zenodo'
                poster.name = data.get('metadata', {}).get('title', None)
                poster.url = data.get('links', {}).get('doi', None)
                poster.description = description
                poster.datePublished = data.get('metadata', {}).get('publication_date')
                poster.license = data.get('metadata', {}).get('license', {}).get('id')

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
                    poster.author.append(author)

                language = ''
                if 'language' in data['metadata']:
                    language = data['metadata']['language']
                poster.inLanguage.append(language)

                keywords = data['metadata'].get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        for key in keyword.split(","):
                            poster.keywords.append(key)
                elif isinstance(keywords, dict):
                    for keyword in keywords.get('buckets', []):
                        for items in keyword:
                            poster.keywords.append(items['key'])
                else:
                    poster.keywords.append('')

                results['resources'].append(poster)

            elif resource_type == 'dataset':
                dataset = Dataset()
                dataset.source = 'Zenodo'
                dataset.name = data.get('metadata', {}).get('title', None)
                dataset.url = data.get('links', {}).get('doi', None)
                dataset.description = description
                dataset.datePublished = data.get('metadata', {}).get('publication_date')
                dataset.license = data.get('metadata', {}).get('license', {}).get('id')

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
                    dataset.author.append(author)

                language = ''
                if 'language' in data['metadata']:
                    language = data['metadata']['language']
                dataset.inLanguage.append(language)

                keywords = data['metadata'].get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        for key in keyword.split(","):
                            dataset.keywords.append(key)
                elif isinstance(keywords, dict):
                    for keyword in keywords.get('buckets', []):
                        for items in keyword:
                            dataset.keywords.append(items['key'])
                else:
                    dataset.keywords.append('')

                results['resources'].append(dataset)

            elif resource_type == 'software':
                software = CreativeWork()
                software.source = 'Zenodo'
                software.name = data.get('metadata', {}).get('title', None)
                software.url = data.get('links', {}).get('doi', None)
                software.description = description
                software.datePublished = data.get('metadata', {}).get('publication_date')
                software.license = data.get('metadata', {}).get('license', {}).get('id')

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
                    software.author.append(author)

                language = ''
                if 'language' in data['metadata']:
                    language = data['metadata']['language']
                software.inLanguage.append(language)

                keywords = data['metadata'].get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        for key in keyword.split(","):
                            software.keywords.append(key)
                elif isinstance(keywords, dict):
                    for keyword in keywords.get('buckets', []):
                        for items in keyword:
                            software.keywords.append(items['key'])
                else:
                    software.keywords.append('')

                results['resources'].append(software)

            
    logger.info(f'Got {len(results)} records from Zenodo')
