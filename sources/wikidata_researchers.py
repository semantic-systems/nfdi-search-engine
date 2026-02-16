from objects import thing, Article, Author, Organization, Person
from sources import data_retriever
from typing import Iterable, Dict, Any, List
import utils
from string import Template
from datetime import datetime
from dateutil import parser
from sources.base import BaseSource
from main import app

class WIKIDATA_Researchers(BaseSource):
    SOURCE = 'WIKIDATA - Researchers'
    @utils.handle_exceptions
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
            "number_of_records" : app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']
        }
        query = query_template.substitute(replacement_dict)
        query = ' '.join(query.split())
        search_result = data_retriever.retrieve_data(source=self.SOURCE,
                                                     base_url=app.config['DATA_SOURCES'][self.SOURCE].get(
                                                         'search-endpoint', ''),
                                                     search_term=query,
                                                     failed_sources=failed_sources)
        return search_result

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        hits = raw.get("results", {}).get("bindings", [])
        total_hits = len(hits)
        utils.log_event(type="info", message=f"{self.SOURCE} - {total_hits} records matched; pulled top {total_hits}")
        return hits

    @utils.handle_exceptions
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

    @utils.handle_exceptions
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

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search Wikidata researchers.
    """
    WIKIDATA_Researchers().search(source, search_term, results, failed_sources)


# @utils.handle_exceptions
# def get_researcher(source: str, orcid: str, source_id: str, researchers):
#     """
#     Fetch a single researcher by ORCID and map it to an Author object.
#     """
#     if not orcid.startswith("https://orcid.org"):
#         orcid = "https://orcid.org/" + orcid
#
#     hit = data_retriever.retrieve_object(
#         source=source,
#         base_url=app.config["DATA_SOURCES"][source].get("get-researcher-endpoint", ""),
#         identifier=orcid
#     )
#
#     if not hit:
#         return
#
#     researcher = Author()
#     researcher.url = orcid
#     researcher.identifier = hit.get("ids", {}).get("orcid", "").replace("https://orcid.org/", "")
#     researcher.name = hit.get("display_name", "")
#
#     # Alternate names
#     alias = hit.get("display_name_alternatives", [])
#     if isinstance(alias, str):
#         researcher.alternateName.append(alias)
#     elif isinstance(alias, list):
#         for _alias in alias:
#             researcher.alternateName.append(_alias)
#
#     # Affiliations
#     affiliations = hit.get("affiliations", [])
#     if isinstance(affiliations, list):
#         for affiliation in affiliations:
#             institution = affiliation.get("institution", {})
#             if isinstance(institution, dict):
#                 _organization = Organization()
#                 _organization.name = institution.get("display_name", "")
#                 years = affiliation.get("years", [])
#                 if len(years) > 1:
#                     _organization.keywords.append(f"{years[-1]}-{years[0]}")
#                 elif len(years) == 1:
#                     _organization.keywords.append(f"{years[0]}")
#                 researcher.affiliation.append(_organization)
#
#     # Research areas (topics)
#     topics = hit.get("topics", [])
#     if isinstance(topics, list):
#         for topic in topics:
#             name = topic.get("display_name", "")
#             if name:
#                 researcher.researchAreas.append(name)
#
#     # Source information
#     _source = thing()
#     _source.name = source
#     openalex_id = hit.get("ids", {}).get("openalex", "").replace("https://openalex.org/", "")
#     _source.identifier = openalex_id
#     researcher.source.append(_source)
#
#     # Search OpenAlex for author's publications
#     researcher_publications = {
#         "publications": [],
#         "others": [],
#     }
#     openalex_id_full = hit.get("id", "").replace("https://openalex.org/", "")
#     url = app.config["DATA_SOURCES"][source].get("get-researcher-publications-endpoint", "") + openalex_id_full
#     openalex_publications.get_publications("OPENALEX - Publications", url, researcher_publications, [])
#     researcher.works.extend(researcher_publications["publications"])
#
#     researchers.append(researcher)
#
#
# def convert_to_string(value):
#     """
#     Helper function to convert various value types to string representation.
#     Note: This function appears to be unused but is kept for backward compatibility.
#     """
#     if isinstance(value, list):
#         return ", ".join(convert_to_string(item) for item in value if item not in ("", [], {}, None))
#     elif hasattr(value, "__dict__"):  # Check if the value is an instance of a class
#         details = vars(value)
#         return ", ".join(
#             f"{key}: {convert_to_string(val)}"
#             for key, val in details.items()
#             if val not in ("", [], {}, None)
#         )
#     return str(value)
#
