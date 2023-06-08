import requests
import logging
from objects import Person, Article
from string import Template
import pandas as pd


# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


def wikidata_search(search_string: str, results):
    wikidata_article_search(search_string, results)
    # wikidata_person_search(search_string, results)
    return results


def wikidata_article_search(search_string: str, results):
    url = 'https://query.wikidata.org/sparql'
    query_template = Template('''
 SELECT DISTINCT ?item ?label (year(?date) as ?dateYear) ?authorsLabel
  WHERE
  {
    SERVICE wikibase:mwapi
    {
      bd:serviceParam wikibase:endpoint "www.wikidata.org";
                      wikibase:api "Generator";
                      mwapi:generator "search";
                      mwapi:gsrsearch "$search_string";
                      mwapi:gsrlimit "150".
      ?item wikibase:apiOutputItem mwapi:title.
    }
    ?item rdfs:label ?label. FILTER( LANG(?label)="en" )


    ?item wdt:P31/wdt:P279* wd:Q11826511.
    #wd:Q11826511 ^wdt:P279*/^wdt:P31 ?item.
    ?item wdt:P577 ?date .
    ?item wdt:P50|wdt:P2093 ?authors .
    SERVICE wikibase:label {
      bd:serviceParam wikibase:language "en" .
  }
  }
  ''')
    response = requests.get(url,
                            params={'format': 'json', 'query': query_template.substitute(search_string=search_string)})
    logger.debug(f'DBLP response status code: {response.status_code}')
    logger.debug(f'DBLP response headers: {response.headers}')

    if response.status_code != 404:
        data = response.json()
        if data["results"]["bindings"]:
            result_df = pd.json_normalize(data['results']['bindings'])
            df = result_df[['item.value', 'label.value', 'dateYear.value', 'authorsLabel.value']]
            df.columns = ['url', 'title', 'date', 'authors']

            df = df.groupby(['url', 'date', 'title'])["authors"].apply(list).reset_index()
            df_dict = df.to_dict('records')

            for row in df_dict:
                results.append(Article(
                    title=row['title'],
                    url=row['url'],
                    authors=', '.join(row['authors']),
                    description='',
                    date=row['date']
                ))
