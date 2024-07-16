import requests
from objects import thing, Article, Author, Organization
import logging
import utils
from sources import data_retriever
from string import Template
from datetime import datetime
from dateutil import parser
import traceback

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):

    source = "WIKIDATA Researchers"

    try:

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

        query = query_template.substitute(search_string=search_term)
        query = ' '.join(query.split())

        search_result = data_retriever.retrieve_data(source=source,
                                                     base_url=utils.config["search_url_wikidata"],
                                                     search_term=query,
                                                     results=results)

        hits = search_result.get("results", {}).get("bindings", [])
        total_hits = len(hits)
        logger.info(f'{source} - {total_hits} hits found')

        if int(total_hits) > 0:
            for hit in hits:

                    # this block should be updated to researchers

                    publication = Article()

                    publication.name = hit.get("label", {}).get("value","")
                    publication.url = hit.get("item", {}).get("value","")
                    publication.identifier = "" #DOI is available for few; we need to update the sparql query to fetch this information
                    publication.datePublished = datetime.strftime(parser.parse(hit.get('date', {}).get('value', "")), '%Y-%m-%d')

                    authorsLabels = hit.get("authorsLabel", {}).get("value","")
                    for authorsLabel in authorsLabels.rstrip(",").split(","):
                        _author = Author()
                        _author.type = 'Person'
                        _author.name = authorsLabel
                        _author.identifier = "" #ORCID is available for few; we need to update the sparql query to pull this information
                        publication.author.append(_author)

                    authorsStrings = hit.get("authorsString", {}).get("value","")
                    for authorsString in authorsStrings.rstrip(",").split(","):
                        _author = Author()
                        _author.type = 'Person'
                        _author.name = authorsString
                        _author.identifier = ""
                        publication.author.append(_author)

                    _source = thing()
                    _source.name = 'WIKIDATA'
                    _source.identifier = hit['item'].get('value', "").replace("http://www.wikidata.org/", "") # remove the base url and only keep the ID
                    _source.url = hit['item'].get('value', "")
                    publication.source.append(_source)

                    results['publications'].append(publication)

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())