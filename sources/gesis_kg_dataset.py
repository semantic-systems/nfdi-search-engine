from objects import thing, Article, Author, Dataset
from sources import data_retriever
from typing import Iterable, Dict, Any, List
import utils
from main import app
from string import Template

from sources.base import BaseSource

class GESIS_KG_Dataset(BaseSource):

    SOURCE = 'GESIS KG - Dataset'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        query_template = Template('''
                                PREFIX schema:<https://schema.org/>
                                PREFIX rdfs:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                                SELECT ?dataset ?title ?doi ?datePublished ?license ?version ?publisher ?dateModified ?dateCreated
                                        (GROUP_CONCAT(DISTINCT ?contributor_name; SEPARATOR="; ") AS ?contributors)
                                        (GROUP_CONCAT(DISTINCT ?author_name; SEPARATOR="; ") AS ?authors)
                                        (GROUP_CONCAT(DISTINCT ?provider; SEPARATOR="\n ") AS ?providers)
                                        (GROUP_CONCAT(DISTINCT ?inLanguage; SEPARATOR="; ") AS ?languages)
                                        (GROUP_CONCAT(DISTINCT ?sourceInfo; SEPARATOR="\n ") AS ?sourceInfos)
                                        (GROUP_CONCAT(DISTINCT ?category; SEPARATOR="; ") AS ?categories)
                                        (GROUP_CONCAT(DISTINCT ?abstract; SEPARATOR="\n ") AS ?abstracts) 
                                        (GROUP_CONCAT(DISTINCT ?comment; SEPARATOR="\n ") AS ?comments) 
                                        (GROUP_CONCAT(DISTINCT ?conditionsOfAccess; SEPARATOR="\n ") AS ?conditionsOfAccesses)
                                        (GROUP_CONCAT(DISTINCT ?spatialCoverage_name; SEPARATOR="\n ") AS ?spatialCoverages)
                                WHERE {
                                    ?dataset rdfs:type schema:Dataset .
                                    ?dataset schema:name ?title . FILTER(CONTAINS(?title, "$search_string"))

                                    OPTIONAL { ?dataset <https://data.gesis.org/gesiskg/schema/doi> ?doi . }
                                    OPTIONAL { ?dataset schema:abstract ?abstract . }
                                    OPTIONAL { ?dataset schema:datePublished ?datePublished . }
                                    OPTIONAL { ?dataset schema:provider ?provider . }
                                    OPTIONAL { ?dataset schema:publisher ?publisher . }
                                    OPTIONAL { ?dataset schema:inLanguage ?inLanguage . }
                                    OPTIONAL { ?dataset schema:version ?version . }
                                    OPTIONAL { ?dataset <https://data.gesis.org/gesiskg/schema/category> ?category . }
                                    OPTIONAL { ?dataset <https://data.gesis.org/gesiskg/schema/sourceInfo> ?sourceInfo . }
                                    OPTIONAL { ?dataset <https://data.gesis.org/gesiskg/schema/license> ?license . }
                                    OPTIONAL { ?dataset schema:comment ?comment . }
                                    OPTIONAL { ?dataset schema:conditionsOfAccess ?conditionsOfAccess . }
                                    OPTIONAL { ?dataset schema:dateModified ?dateModified .}
                                    OPTIONAL { ?dataset schema:dateCreated ?dateCreated .}
                                    OPTIONAL { ?dataset schema:spatialCoverage ?spatialCoverage .
                                                ?spatialCoverage schema:name ?spatialCoverage_name .}
                                    OPTIONAL { ?dataset schema:contributor ?contributor . 
                                                ?contributor schema:name ?contributor_name .}
                                    OPTIONAL { ?dataset schema:author ?author .
                                            ?author schema:name ?author_name . }
                                }
                                GROUP BY ?dataset ?title ?doi ?datePublished ?license ?version ?publisher ?dateModified ?dateCreated
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
    def map_hit(self, hit: Dict[str, Any]) -> Dataset:
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        dataset = Dataset()
        dataset.additionalType = "DATASET"
        dataset.identifier = hit.get("doi", {}).get("value", "")
        dataset.name = hit.get("title", {}).get("value", "")
        dataset.url = hit.get("dataset", {}).get("value", "").strip()

        dataset.datePublished = hit.get('datePublished', {}).get('value', "")
        dataset.dateCreated = hit.get('dateCreated', {}).get('value', "")
        dataset.dateModified = hit.get('dateModified', {}).get('value', "")
        dataset.version = hit.get('version', {}).get('value', "")
        dataset.license = hit.get('license', {}).get('value', "")
        dataset.publisher = hit.get('publisher', {}).get('value', "")

        languages = hit.get("languages", {}).get("value", "")
        if languages:
            for language in languages.strip().split(" "):
                dataset.inLanguage.append(language)
        # dataset.sourceOrganization = hit.get("providers", {}).get("value", "")
        dataset.description = hit.get("abstract", {}).get("value", "")
        # dataset.publication = hit.get("sourceInfos", {}).get("value", "")

        authors = hit.get("authors", {}).get("value", "")
        contributors = hit.get("contributors", {}).get("value", "")
        authors_list = [name for name in (authors + ";" + contributors).strip(", ").split(";") if name]
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
            dataset.author.append(_author)

        _source = thing()
        _source.name = 'GESIS KG - Dataset'
        _source.originalSource = dataset.publisher
        _source.identifier = dataset.identifier
        _source.url = dataset.url
        dataset.source.append(_source)

        return dataset
    
    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        if hits:
            for hit in hits:
                dataset = self.map_hit(hit)
                results['resources'].append(dataset)
        
def search(source_name: str, search_term: str, results: dict, failed_sources: list):
    """
    Entrypoint to search GESIS KG datasets.
    """
    GESIS_KG_Dataset().search(source_name, search_term, results, failed_sources)