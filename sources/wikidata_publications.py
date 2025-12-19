from objects import thing, Article, Author
from sources import data_retriever
from string import Template
from datetime import datetime
from dateutil import parser
from typing import Iterable, Dict, Any, List
import utils
from main import app

from sources.base import BaseSource
class WIKIDATA_Publication(BaseSource):

    SOURCE = 'WIKIDATA - Publications'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        query_template = Template('''
                                    SELECT DISTINCT ?item ?label ?date ?doi
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
                                        ?item wdt:P356 ?doi .
                                        ?item wdt:P50 ?authors.
                                        ?authors rdfs:label ?authorsName . FILTER( LANG(?authorsName)="en" )
                                        optional {?item wdt:P2093 ?authors2.}
                                        }
                                    GROUP BY ?item ?label ?date ?doi 
                                      LIMIT $number_of_records

                                        ''')
        replacement_dict = {
            "search_string": search_term,
            "number_of_records": app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']
        }
        query = query_template.substitute(replacement_dict)
        query = ' '.join(query.split())
        search_result = data_retriever.retrieve_data(source=self.SOURCE,
                                                     base_url=app.config['DATA_SOURCES'][self.SOURCE].get('search-endpoint', ''),
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
        print(str(total_hits) + "from WIKIDATA Publications")
        if int(total_hits) > 0:
            return hits
        return None




# @utils.handle_exceptions
# def search(source: str, search_term: str, results, failed_sources):
#     query_template = Template('''
#                             SELECT DISTINCT ?item ?label ?date ?doi
#                             (group_concat(DISTINCT ?authorsName; separator=",") as ?authorsLabel)
#                             (group_concat(DISTINCT ?authors2; separator=",") as ?authorsString)
#                                 WHERE
#                                 {
#                                 SERVICE wikibase:mwapi
#                                 {
#                                     bd:serviceParam wikibase:endpoint "www.wikidata.org";
#                                                     wikibase:limit "once";
#                                                     wikibase:api "Generator";
#                                                     mwapi:generator "search";
#                                                     mwapi:gsrsearch "$search_string";
#                                                     mwapi:gsrlimit "max".
#                                     ?item wikibase:apiOutputItem mwapi:title.
#                                 }
#                                 ?item rdfs:label ?label. FILTER( LANG(?label)="en" )
#                                 ?item wdt:P31/wdt:P279* wd:Q11826511.
#                                 ?item wdt:P577 ?date .
#                                 ?item wdt:P356 ?doi .
#                                 ?item wdt:P50 ?authors.
#                                 ?authors rdfs:label ?authorsName . FILTER( LANG(?authorsName)="en" )
#                                 optional {?item wdt:P2093 ?authors2.}
#                                 }
#                             GROUP BY ?item ?label ?date ?doi
#                               LIMIT $number_of_records
#
#                                 ''')
#
#     replacement_dict = {
#         "search_string" : search_term,
#         "number_of_records" : app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']
#     }
#     query = query_template.substitute(replacement_dict)
#     query = ' '.join(query.split())
#     search_result = data_retriever.retrieve_data(source=source,
#                                                 base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
#                                                 search_term=query,
#                                                 failed_sources=failed_sources)
#
#     hits = search_result.get("results", {}).get("bindings", [])
#     total_hits = len(hits)
#     utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {total_hits}")
#
#     if int(total_hits) > 0:
#         for hit in hits:
#
#             publication = Article()
#
#             publication.name = hit.get("label", {}).get("value","")
#             publication.url = hit.get("item", {}).get("value","")
#             publication.identifier = hit.get("doi", {}).get("value","") #DOI is available for few; we need to update the sparql query to fetch this information
#             # print(publication.identifier)
#             publication.datePublished = datetime.strftime(parser.parse(hit.get('date', {}).get('value', "")), '%Y-%m-%d')
#
#             authorsLabels = hit.get("authorsLabel", {}).get("value","")
#             for authorsLabel in authorsLabels.rstrip(",").split(","):
#                 _author = Author()
#                 _author.additionalType = 'Person'
#                 _author.name = authorsLabel
#                 _author.identifier = "" #ORCID is available for few; we need to update the sparql query to pull this information
#                 author_source = thing(
#                     name=source,
#                     identifier=_author.identifier,
#                 )
#                 _author.source.append(author_source)
#                 publication.author.append(_author)
#
#             authorsStrings = hit.get("authorsString", {}).get("value","")
#             for authorsString in authorsStrings.rstrip(",").split(","):
#                 _author = Author()
#                 _author.additionalType = 'Person'
#                 _author.name = authorsString
#                 _author.identifier = ""
#                 author_source = thing(
#                     name=source,
#                     identifier=_author.identifier,
#                 )
#                 _author.source.append(author_source)
#                 publication.author.append(_author)
#
#             _source = thing()
#             _source.name = 'WIKIDATA'
#             _source.identifier = hit['item'].get('value', "").replace("http://www.wikidata.org/", "") # remove the base url and only keep the ID
#             _source.url = hit['item'].get('value', "")
#             publication.source.append(_source)
#
#             if publication.identifier != "":
#                 results['publications'].append(publication)
#             else:
#                 results['others'].append(publication)