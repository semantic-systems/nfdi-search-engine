import requests
from objects import thing, Article, Author
import logging
import utils
from sources import data_retriever
from string import Template
from datetime import datetime
from dateutil import parser

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):
    
    source = "WIKIDATA Publications"

    try:

        query_template = Template('''
                                SELECT DISTINCT ?item ?label ?date 
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