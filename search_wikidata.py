import requests
import logging
from objects import Person, Article
from string import Template
import pandas as pd


# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


def wikidata_search(search_string: str, results):
    """ Obtain the results from Wikidata request and handles them accordingly.

      Args:
          search_string: keyword(s) to search for
          results: search answer formatted into the data types of Person and Article

      Returns:
            the results array
      """

    wikidata_article_search(search_string, results)
    # wikidata_person_search(search_string, results)

    logger.info(f"Got {len(results)} author and publication records from Wikidata")
    return results


def wikidata_article_search(search_string: str, results):
    url = 'https://query.wikidata.org/sparql'
    headers = {'User-Agent': 'NFDI4DS-Research'}
    query_template = Template('''
SELECT DISTINCT ?item ?label (year(?date)as ?dateYear) (group_concat(DISTINCT ?authors2; separator=", ") as ?authorsString) ?authorsLabel

  WHERE
  {
    SERVICE wikibase:mwapi
    {
      bd:serviceParam wikibase:endpoint "www.wikidata.org";
                      wikibase:limit 100;
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
    ?item wdt:P50 ?authors.
    ?item wdt:P2093 ?authors2.
    
SERVICE wikibase:label {bd:serviceParam wikibase:language "en" .}
  }
GROUP BY ?item ?label ?date ?authorsLabel
ORDER BY DESC(?dateYear)
  ''')

    response = requests.get(url,
                            params={'format': 'json', 'query': query_template.substitute(search_string=search_string),
                                    }, timeout=(3,15), headers=headers)
    logger.debug(f'DBLP response status code: {response.status_code}')
    logger.debug(f'DBLP response headers: {response.headers}')

    if response.status_code != 404 and response.status_code != 408 and response.status_code != 504:
        data = response.json()
        if data["results"]["bindings"]:
            result_df = pd.json_normalize(data['results']['bindings'])
            df = result_df[['item.value', 'label.value', 'dateYear.value', 'authorsLabel.value', 'authorsString.value']]
            df.columns = ['url', 'title', 'date', 'authors', 'authors2']
            df = df.groupby(['url', 'date', 'title', 'authors2'])["authors"].apply(lambda x: ", ".join(x)).reset_index()
            df['allAuthors'] = df['authors'].map(str) + ', ' + df['authors2'].map(str)
            df = df.sort_values(by=['date'], ascending=False).reset_index()
            df_dict = df.to_dict('records')

            for row in df_dict:
                results.append(Article(
                    title=row['title'],
                    url=row['url'],
                    authors=row['allAuthors'],
                    description='',
                    date=row['date']
                ))
