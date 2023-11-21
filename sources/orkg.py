import requests
import logging
import json
import utils
from objects import thing, Article, Author
from sources import data_retriever
import traceback
import re

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


@utils.timeit
def search(search_term: str, results):
    source = "ORKG"
    details_api = "https:/orkg.org/api/"

    try:

        search_result = data_retriever.retrieve_data(source=source,
                                                     base_url=utils.config["search_url_orkg"],
                                                     search_term=search_term,
                                                     results=results)

        total_hits = search_result['content']
        print(total_hits)
        # ids: list = []
        for hit in total_hits:
            id = hit.get('id', None)
            classes = hit.get('classes', [])
            print(classes)
            if 'Paper' in classes:
                api_url = details_api + 'papers/' + id
                response = requests.get(api_url)
                paper = response.json()
                print('orkg results: ')
                print(paper)

        logger.info(f'{source} - {total_hits} records matched; pulled top {total_hits}')

        if int(total_hits) > 0:
            hits = search_result['hits']['hits']

            for hit in hits:

                hit_source = hit.get('_source', {})

                publication = Article()
                publication.name = hit_source.get("name", "")
                publication.url = hit_source.get("id", "")
                publication.identifier = re.sub('^.*doi\.org\/', '', hit_source.get("id", ""))
                publication.datePublished = hit_source.get("datePublished", "")
                publication.license = hit_source.get("license", {}).get("id", "")

                publication.description = utils.remove_html_tags(hit_source.get("description", ""))
                publication.abstract = publication.description

                publishers = hit_source.get("publisher", [])
                if len(publishers) > 0:
                    publication.publication = publishers[0].get("name", "")

                for author in hit_source.get("creator", []):
                    if author['type'] == 'Person':
                        _author = Author()
                        _author.type = 'Person'
                        _author.name = author.get("name", "")
                        _author.identifier = author.get("id", "").replace('https://orcid.org/', '')
                        publication.author.append(_author)

                _source = thing()
                _source.name = source
                _source.identifier = hit.get("_id", "")
                _source.url = "https://resodate.org/resources/" + hit.get("_id", "")
                publication.source.append(_source)

                # information only limited to this source
                publication.image = hit_source.get("image", "")
                keywords = hit_source.get("keywords", None)
                if keywords:
                    for keyword in keywords:
                        publication.keywords.append(keyword)

                languages = hit_source.get("inLanguage", None)
                if languages:
                    for language in languages:
                        publication.inLanguage.append(language)

                encodings = hit_source.get("encoding", None)
                if encodings:
                    for encoding in encodings:
                        publication.encoding_contentUrl = encoding.get("contentUrl", "")
                        publication.encodingFormat = encoding.get("encodingFormat", "")

                results['publications'].append(publication)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())
