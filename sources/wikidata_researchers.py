from typing import Iterable, Dict, Any, List
from string import Template

from sources import data_retriever
from objects import thing, Article, Author, Organization, Person
from sources.base import BaseSource
from config import Config


class WIKIDATA_Researchers(BaseSource):
    SOURCE = 'WIKIDATA - Researchers'
    
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
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
            "number_of_records" : Config.NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT
        }
        query = query_template.substitute(replacement_dict)
        query = ' '.join(query.split())
        search_result = data_retriever.retrieve_data(source=self.SOURCE,
                                                     base_url=Config.DATA_SOURCES[self.SOURCE].get(
                                                         'search-endpoint', ''),
                                                     search_term=query,
                                                     failed_sources=failed_sources)
        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        hits = raw.get("results", {}).get("bindings", [])
        total_hits = len(hits)
        self.log_event(type="info", message=f"{self.SOURCE} - {total_hits} records matched; pulled top {total_hits}")
        return hits

    def map_hit(self, hit: Dict[str, Any])-> Author:
        """
        Map a single hit dict from the source to an Author object.
        """
        author = Author()
        orcid = hit.get("orcid", {}).get("value", "").replace("https://orcid.org", "")
        author.identifier = orcid
        author.additionalType = "Person"

        author.name = hit.get('itemLabel', {}).get('value', '')

        affiliation_data = hit.get('employerSampleLabel', {})
        if isinstance(affiliation_data, dict):
            affiliation_name = affiliation_data.get('value', '')
            if affiliation_name:
                author.affiliation.append(Organization(name=affiliation_name))
        _source = thing()
        _source.name = self.SOURCE
        uri = hit.get('item', {}).get('value', "") #.replace("http://www.wikidata.org/", "")
        _source.identifier = uri
        _source.url = uri
        author.source.append(_source)

        author.works_count = ''
        author.cited_by_count = ''

        return author

    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)
        if len(hits) > 0:
            for hit in hits:
                author = self.map_hit(hit=hit)
                if author.identifier != "":
                    results["researchers"].append(author)


def search(source: str, search_term: str, results, failed_sources, tracking=None):
    """
    Entrypoint to search Wikidata researchers.
    """
    WIKIDATA_Researchers(tracking).search(source, search_term, results, failed_sources)
