import requests
import logging
import json
import utils
from objects import Article, Person
import re

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):
    try:
        url = 'https://resodate.org/resources/api/search/oer_data/_search?pretty&q="' + search_term.replace(' ',
                                                                                                            '+') + '"'
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json',
                   'User-Agent': 'nfdi4dsBot/1.0 (https://https://www.nfdi4datascience.de/nfdi4dsBot/; '
                                 'nfdi4dsBot@nfdi4datascience.de) '
                   }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            search_result = response.json()

            total_hits = search_result['hits']['total']['value']

            if total_hits > 0:
                hits = search_result['hits']['hits']

                # regex pattern to remove html tags such as <div>, <p>, and <br>
                regex_pattern = r"<[\S]+>"

                for hit in hits:
                    hit_source = hit['_source']
                    publication = Article()
                    publication.source = 'RESODATE'
                    publication.name = hit_source["name"]                    
                    publication.url = hit_source['id']
                    publication.description = utils.remove_html_tags(hit_source["description"])
                    publication.abstract = utils.remove_html_tags(hit_source["description"])
                    publication.keywords = hit_source['keywords']
                    for creator in hit_source['creator']:
                        if creator['type'] == 'Person':
                            author = Person()
                            author.name = creator['name']
                            author.identifier = creator['id'] 
                            publication.author.append(author)               
                    
                    
                    results['publications'].append(publication)

                    # results.append(
                    #     Article(
                    #         # title=hit_source["name"],
                    #         # url=hit_source['id'],
                    #         authors=', '.join([creator['name'] for creator in hit_source['creator']]),
                    #         # description=description,
                    #         date=str(hit_source["datePublished"])
                    #     )
                    # )
                    

        # pprint(results)

    except Exception as ex:
        print(ex.__str__)
