from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app
from string import Template
from datetime import datetime
from dateutil import parser

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
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
                                                    mwapi:gsrlimit "max".
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
                              LIMIT $number_of_records
                            
                                ''')    

    replacement_dict = {
        "search_string" : search_term,
        "number_of_records" : app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']
    }
    query = query_template.substitute(replacement_dict)
    query = ' '.join(query.split())
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=query,
                                                failed_sources=failed_sources) 
    
    hits = search_result.get("results", {}).get("bindings", [])        
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {total_hits}")

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

            if publication.identifier != "":
                results['publications'].append(publication)
            else:
                results['others'].append(publication)

            