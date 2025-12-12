from objects import thing, Article, Author, CreativeWork
from sources import data_retriever
from typing import Iterable, Dict, Any, List
import utils
from main import app
from sources.base import BaseSource


class CROSSREF_Publications(BaseSource):

    SOURCE = 'CROSSREF - Publications'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(source=self.SOURCE, 
                                                    base_url=app.config['DATA_SOURCES'][self.SOURCE].get('search-endpoint', ''),
                                                    search_term=search_term,
                                                    failed_sources=failed_sources) 
        
        return search_result
    
    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        total_records_found = raw['message']['total-results']
        hits = raw['message'].get("items", [])
        total_hits = len(hits)
        utils.log_event(type="info", message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}") 

        return hits

    @utils.handle_exceptions
    def map_hit(self, source_name: str, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        publication = Article() 
        publication.additionalType = hit.get("type", "")
        titles = hit.get("title", [])    
        if len(titles) > 0:
            publication.name = utils.remove_html_tags(titles[0])       
        publication.url = hit.get("URL", "")
        publication.identifier = hit.get("DOI", "").replace("https://doi.org/", "")
        publication.datePublished = hit.get("created", {}).get("date-time","") 
        publication.inLanguage.append(hit.get("language", ""))
        licenses = hit.get("license", [])
        if len(licenses) > 0:
            publication.license = licenses[0].get("URL", "")
        publication.publication = hit.get("publisher", "")

        publication.description = utils.remove_html_tags(hit.get("abstract",""))
        publication.abstract = publication.description

        publication.referenceCount = hit.get("reference-count", "")
        publication.citationCount = hit.get("is-referenced-by-count", "")

        authorships = hit.get("author", [])                        
        for authorship in authorships:
            _author = Author()
            _author.additionalType = 'Person'
            _author.name = authorship.get("given", "") + " " + authorship.get("family", "")
            _author.identifier = authorship.get("orcid", "")

            author_source = thing(
                name=self.SOURCE,
                identifier=_author.identifier,
            )

            _author.source.append(author_source)
            publication.author.append(_author)
        
        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = publication.identifier
        _source.url = publication.url                                          
        publication.source.append(_source)

        return publication

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        for hit in hits:
            publication = self.map_hit(hit)
            if publication:
                results['publications'].append(publication)


    @utils.handle_exceptions
    def get_publication(self, doi: str):
        search_result = data_retriever.retrieve_object(source=self.SOURCE, 
                                                        base_url=app.config['DATA_SOURCES'][self.SOURCE].get('get-publication-endpoint', ''),
                                                        identifier=doi)
        
        if search_result:
            search_result = search_result.get('message',{})
            return self.map_hit(self.SOURCE, search_result)

    @utils.handle_exceptions
    def get_dois_references(self, source: str, doi: str) -> list:
        """
        Fetches the references for a given DOI from the specified source.

        Args:
            source (str): The source from which to fetch references.
            doi (str): The DOI of the article to fetch references for.

        Returns:
            list: A list of DOIs that are referenced by the given DOI.
        """
        search_result = data_retriever.retrieve_object(source=self.SOURCE, 
                                                        base_url=app.config['DATA_SOURCES'][source].get('get-publication-references-endpoint', ''),
                                                        identifier=doi,
                                                        quote=False)
        
        if search_result:
            search_result = search_result.get('message',{})

            if "reference" not in search_result:
                return []

            dois = [ref.get("DOI", "") for ref in search_result["reference"] if ref.get("DOI", "")]

            return dois
        
        return []

    @utils.handle_exceptions
    def get_publication_references(self, source: str, doi: str):
        search_result = data_retriever.retrieve_object(source=self.SOURCE, 
                                                        base_url=app.config['DATA_SOURCES'][source].get('get-publication-references-endpoint', ''),
                                                        identifier=doi)
        if search_result:
            search_result = search_result.get('message',{})
            digitalObj = self.map_hit(self.SOURCE, search_result)    
            
            references = search_result.get("reference", [])                        
            for reference in references:
                referenced_publication = Article() 
                referenced_publication.identifier = reference.get("DOI", "") 

                _source = thing()
                _source.name = self.SOURCE
                _source.identifier = referenced_publication.identifier
                _source.url = referenced_publication.url                                          
                referenced_publication.source.append(_source)

                structured_reference_text = []  
                structured_reference_text.append(reference.get("author", "")) 
                reference_year = reference.get("year", "")
                if reference_year  != "":
                    structured_reference_text.append("(" + reference_year + ")")
                structured_reference_text.append(reference.get("article-title", ""))
                structured_reference_text.append(reference.get("series-title", ""))
                structured_reference_text.append(reference.get("journal-title", ""))
                structured_reference_text.append(reference.get("unstructured", ""))        
                referenced_publication.text = ('. ').join(filter(None, structured_reference_text))
                digitalObj.reference.append(referenced_publication)     
            
            return digitalObj

def search(source_name: str, search_term: str, results: dict, failed_sources: list):
    """
    Entrypoint to search CROSSREF publications.
    """
    CROSSREF_Publications().search(source_name, search_term, results, failed_sources)

def get_publication(source, doi, source_id, publications) -> None:
    source = CROSSREF_Publications()

    publication = source.get_publication(doi)
    if publication:
        publications.append(publication)

def get_dois_references(self, source: str, doi: str):
    return CROSSREF_Publications().get_dois_references(source, doi)

def get_publication_references(self, source: str, doi: str):
    return CROSSREF_Publications().get_publication_references(source, doi)