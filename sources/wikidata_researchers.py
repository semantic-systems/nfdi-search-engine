from objects import thing, Article, Author, Organization
from sources import data_retriever
import utils
from main import app
from string import Template
from datetime import datetime
from dateutil import parser

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
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
            author = Author()
            # info = hit.get('info',{})
            author.orcid = hit.get("orcid", {}).get("value", "")
            author.identifier = author.orcid
            author.name = hit.get('itemLabel', '').get('value', '')
            affiliations = hit.get('employerSampleLabel', {})
            if isinstance(affiliations, dict):
                author.affiliation.append(Organization(name = affiliations.get('value', {})))
            author.works_count = ''
            author.cited_by_count = ''

            _source = thing()
            _source.name = 'WIKIDATA'
            _source.identifier = hit['item'].get('value', "").replace("http://www.wikidata.org/", "") # hit.get("ids", {}).get("openalex", "")
            _source.url = hit.get("item", {}).get("value", "")                       
            author.source.append(_source)

            results['researchers'].append(author)  
    
