import requests
import logging
import json
import utils
from pprint import pprint
from objects import Article
import re

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

def search(search_term: str, results):

    try:


        url = 'https://resodate.org/resources/api/search/oer_data/_search?pretty&q="' + search_term.replace(' ','+') + '"'
        headers = {'Accept': 'application/json', 
                'Content-Type': 'application/json',
                'User-Agent': 'nfdi4dsBot/1.0 (https://https://www.nfdi4datascience.de/nfdi4dsBot/; nfdi4dsBot@nfdi4datascience.de)'
                }
        # data = { 'size': 20,
        #          'from': 0,
        #          'query': { 'multi_match': { 'query': 'Ricardo Mata', 
        #                                      'fields': ['name', 'description', 'keywords']}},
        #          'sort': [{'id': 'asc'}]}
        
        # data = { 'size': 20,
        #          'from': 0,
        #          'query': { 'match': { '_all': 'Ricardo Mata' } },             
        #          'sort': [{'id': 'asc'}]}

        response = requests.get(url, headers=headers)  

        pprint(response.text)

        if (response.status_code == 200):
            search_result= response.json()

            total_hits = search_result['hits']['total']['value']

            if total_hits > 0:
                hits = search_result['hits']['hits']

                # regex pattern to remove html tags such as <div>, <p>, and <br>
                regex_pattern = r"<[\S]+>"

                for hit in hits:
                    
                    hit_source = hit['_source']
                    results.append(
                        Article(
                            title=hit_source["name"],
                            url=hit_source['id'],
                            authors=', '.join([creator['name'] for creator in hit_source['creator']]),
                            description= re.sub(regex_pattern, '', hit_source["description"], 0, re.MULTILINE),
                            date=str(hit_source["datePublished"])
                        )
                    )
 
        pprint(results)

    except Exception as ex:
        print(ex.__str__)


if __name__ == "__main__":   

    results= []
    # resodate('Ricardo Mata', results)
    search('Abdullah Demir', results)

