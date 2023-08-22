import requests
import logging
from objects import Article, Author
from string import Template
from datetime import datetime
from dateutil import parser

logger = logging.getLogger('nfdi_search_engine')


def search(search_string: str, results):
    """ Obtain the results from Wikidata request and handles them accordingly.

      Args:
          search_string: keyword(s) to search for
          results: search answer are formatted according to schema.org types Article, Author, ...

      Returns:
            the results array
      """
    wikidata_person_search(search_string, results)
    wikidata_article_search(search_string, results)

    logger.info(f"Got {len(results)} author and publication records from Wikidata")
    return results


def wikidata_article_search(search_string: str, results):
    url = 'https://query.wikidata.org/sparql'
    headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
    query_template = Template('''
 SELECT DISTINCT ?item ?label ?date #(year(?date)as ?dateYear)
(group_concat(DISTINCT ?authorsName; separator=",") as ?authorsLabel)
(group_concat(DISTINCT ?authors2; separator=",") as ?authorsString) 
  WHERE
  {
    SERVICE wikibase:mwapi
    {
      bd:serviceParam wikibase:endpoint "www.wikidata.org";
                      wikibase:limit "once";
                      wikibase:api "Generator";
                      mwapi:generator "search";
                      mwapi:gsrsearch "$search_string";
                      mwapi:gsrlimit "150".
      ?item wikibase:apiOutputItem mwapi:title.
    }
    ?item rdfs:label ?label. FILTER( LANG(?label)="en" )
    ?item wdt:P31/wdt:P279* wd:Q11826511.
    ?item wdt:P577 ?date .
    ?item wdt:P50 ?authors.
    ?authors rdfs:label ?authorsName . FILTER( LANG(?authorsName)="en" )
    optional {?item wdt:P2093 ?authors2.}
  }
GROUP BY ?item ?label ?date 
#ORDER BY DESC(?dateYear)
  ''')

    response = requests.get(url,
                            params={'format': 'json', 'query': query_template.substitute(search_string=search_string),
                                    }, headers=headers)
    logger.debug(f'Wikidata article search response status code: {response.status_code}')
    logger.debug(f'Wikidata article search response headers: {response.headers}')

    if response.status_code == 200:
        data = response.json()
        if data["results"]["bindings"]:
            for result in data["results"]["bindings"]:
                publication = Article()
                publication.source = 'Wikidata'
                publication.url = result['item'].get('value', "")
                publication.name = result['label'].get('value', "")
                date_obj = parser.parse(result.get('date', {}).get('value', ""))
                date = datetime.strftime(date_obj, '%Y-%m-%d')
                publication.datePublished = date  # result.get('date', {}).get('value', "")
                if result['authorsLabel'].get("value"):
                    authors_list = result['authorsLabel'].get("value", "").rstrip(",").split(",")
                    for item in authors_list:
                        author = Author()
                        author.name = item
                        author.type = 'Person'
                        publication.author.append(author)
                if result['authorsString'].get("value"):
                    authors_list = result['authorsString'].get("value", "").rstrip(",").split(",")
                    for item in authors_list:
                        author = Author()
                        author.name = item
                        author.type = 'Person'
                        publication.author.append(author)
                results['publications'].append(publication)


def wikidata_person_search(search_string: str, results):
    url = 'https://query.wikidata.org/sparql'
    headers = {'User-Agent': 'https://nfdi-search.nliwod.org/'}
    query_template = Template('''
SELECT DISTINCT ?item ?itemLabel ?orcid (SAMPLE(?employerLabel) as ?employerSampleLabel) ?nationalityLabel ?givenNameLabel ?familyNameLabel
   WHERE
   {
    SERVICE wikibase:mwapi
    {
      bd:serviceParam wikibase:endpoint "www.wikidata.org";
                      wikibase:api "EntitySearch";
                     
                      mwapi:search "$search_string";
                      mwapi:language "en";
                      mwapi:limit "150".
      ?item wikibase:apiOutputItem mwapi:item.
    }
    #?item (wdt:P279*/wdt:P31) wd:Q482980 .
    ?item wdt:P106 ?occ .
    ?occ wdt:P279* wd:Q1650915 .
    OPTIONAL {?item wdt:P496 ?orcid .}
    OPTIONAL {?item wdt:P27 ?nationality.}
    OPTIONAL {?item wdt:P735 ?givenName.}
    OPTIONAL {?item wdt:P734 ?familyName.} 
    OPTIONAL {
      ?item p:P108 ?st.
              ?st ps:P108 ?employer.
              ?employer rdfs:label ?employerLabel. FILTER( LANG(?employerLabel)="en" )
              ?st pq:P580 ?date.
       MINUS {?st pq:P582 ?enddate.}        
    }
    OPTIONAL {?item wdt:P108 ?employer. 
             ?employer rdfs:label ?employerLabel. FILTER( LANG(?employerLabel)="en" )
             }
  
    SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
  }
GROUP by ?item ?itemLabel ?orcid ?nationalityLabel ?givenNameLabel ?familyNameLabel 

      ''')

    response = requests.get(url,
                            params={'format': 'json', 'query': query_template.substitute(search_string=search_string),
                                    }, headers=headers)
    logger.debug(f'Wikidata person search response status code: {response.status_code}')
    logger.debug(f'Wikidata person search response headers: {response.headers}')

    if response.status_code == 200:
        data = response.json()
        if data["results"]["bindings"]:
            for result in data["results"]["bindings"]:
                author = Author()
                author.source = 'Wikidata'
                author.url = result['item'].get('value', "")
                author.name = result['itemLabel'].get('value', "")
                author.givenName = result.get('givenNameLabel', {}).get('value', "")
                author.familyName = result.get('familyNameLabel', {}).get('value', "")
                author.affiliation = result.get('employerSampleLabel', {}).get('value', "")
                author.nationality = result.get('nationalityLabel', {}).get('value', "")
                author.orcid = result.get('orcid', {}).get('value', "")

                results['researchers'].append(author)
