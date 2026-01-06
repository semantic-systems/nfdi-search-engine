from objects import thing, Article, Author
from sources import data_retriever
from typing import Iterable, Dict, Any, List
import utils
from main import app
from string import Template

from sources.base import BaseSource

class GESIS_KG_Publication(BaseSource):

    SOURCE = 'GESIS KG'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        query_template = Template('''
                                PREFIX schema:<https://schema.org/>
                                PREFIX rdfs:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                                
                                SELECT ?publication ?title ?doi ?abstract
                                        (GROUP_CONCAT(DISTINCT ?linksURN; SEPARATOR=", ") AS ?linksURNs) 
                                        (GROUP_CONCAT(DISTINCT ?url; SEPARATOR=", ") AS ?urls)
                                        (GROUP_CONCAT(DISTINCT ?datePub; SEPARATOR=", ") AS ?datePublished)
                                        (GROUP_CONCAT(DISTINCT ?contributor_name; SEPARATOR="; ") AS ?contributors)
                                        (GROUP_CONCAT(DISTINCT ?author_name; SEPARATOR="; ") AS ?authors)
                                        (GROUP_CONCAT(DISTINCT ?provider; SEPARATOR=", ") AS ?providers)
                                        (GROUP_CONCAT(DISTINCT ?inLanguage; SEPARATOR=", ") AS ?languages)
                                        (GROUP_CONCAT(DISTINCT ?sourceInfo; SEPARATOR=", ") AS ?sourceInfos)
                                WHERE {
                                    ?publication rdfs:type schema:ScholarlyArticle .
                                    ?publication schema:name ?title . FILTER(CONTAINS(?title, "$search_string"))
                                    
                                    OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/doi> ?doi . }
                                    OPTIONAL { ?publication schema:abstract ?abstract . }
                                    OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/linksURN> ?linksURN . }
                                    OPTIONAL { ?publication schema:url ?url . }
                                    OPTIONAL { ?publication schema:datePublished ?datePub . }
                                    OPTIONAL { ?publication schema:provider ?provider . }
                                    OPTIONAL { ?publication schema:inLanguage ?inLanguage . }
                                    OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/sourceInfo> ?sourceInfo . }
                                    OPTIONAL { ?publication schema:contributor ?contributor . 
                                                ?contributor schema:name ?contributor_name .}
                                    OPTIONAL { ?publication schema:author ?author .
                                            ?author schema:name ?author_name . }
                                }
                                GROUP BY ?publication ?title ?doi ?abstract
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
        # print(str(total_hits) + "from GESIS KG")
        if int(total_hits) > 0:
            return hits
        return None
    
    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]) -> Article:
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        publication = Article()
        publication.identifier = hit.get("doi", {}).get("value", "")
        publication.name = hit.get("title", {}).get("value", "")
        publication.url =  hit.get("urls", {}).get("value", "").strip() # hit.get("urls", {}).get("value", "")

        #publication.identifier = hit.get("linksURNs", {}).get("value", "")  # DOI is available for few; we need to update the sparql query to fetch this information
        publication.description = hit.get("abstract", {}).get("value", "")
        publication.datePublished = hit.get('datePublished', {}).get('value', "")
        languages = hit.get("languages", {}).get("value", "")
        if languages:
            for language in languages.strip().split(" "):
                publication.inLanguage.append(language)
        #publication.sourceOrganization = hit.get("providers", {}).get("value", "")
        publication.publisher = hit.get("sourceInfos", {}).get("value", "")

        authors = hit.get("authors", {}).get("value", "")
        contributors = hit.get("contributors", {}).get("value", "")
        authors_list = [name for name in (authors + ";" + contributors).strip(", ").split(";") if name ]
        authors_list = list(dict.fromkeys(authors_list))

        for authorsName in authors_list:
            _author = Author()
            _author.additionalType = 'Person'
            _author.name = authorsName
            _author.identifier = ""  # ORCID is available for few; we need to update the sparql query to pull this information
            author_source = thing(
                name=self.SOURCE,
                identifier=_author.identifier,
            )
            _author.source.append(author_source)
            publication.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.originalSource = publication.publisher
        _source.identifier = publication.identifier # hit['publication'].get('value', "") #.replace("http://www.wikidata.org/", "")  # remove the base url and only keep the ID
        _source.url = publication.url #hit['urls'].get('value', "").strip()
        publication.source.append(_source)

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        if hits:
            for hit in hits:
                publication = self.map_hit(hit)
                results['resources'].append(publication)
        


def search(source_name: str, search_term: str, results: dict, failed_sources: list):
    """
    Entrypoint to search GESIS KG publications.
    """
    GESIS_KG_Publication().search(source_name, search_term, results, failed_sources)
