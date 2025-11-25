from objects import thing, Article, Author, CreativeWork
from sources import data_retriever
from typing import Iterable, Dict, Any, List
import utils
from main import app
import requests

source = 'DataCite'

class DataCite:
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                     search_term=search_term,
                                                     failed_sources=failed_sources) 
        
        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        return raw['data']

    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """

        publication = Article()

        publication.additionalType = hit.get("types", {}).get("bibtex", {})

        titles = hit.get("titles", [])
        if len(titles) > 0:
            publication.name = utils.remove_html_tags(titles[0]['title'])

        publication.url = hit.get("url", "")
        publication.identifier = hit.get("doi", "").replace("https://doi.org/", "")
        publication.datePublished = hit.get("created", "")
        publication.inLanguage.append(hit.get("language", ""))

        publication.publication = hit.get("publisher", "")

        rightsList = hit.get("rightsList", [])
        if len(rightsList) > 0:
            publication.license = rightsList[0].get('rights', '')

        descriptions = hit.get('descriptions', [])
        if len(descriptions) > 0:
            publication.description = utils.remove_html_tags(descriptions[0]['description'])
        publication.abstract = publication.description

        publication.referenceCount = hit.get("referenceCount", "")
        publication.citationCount = hit.get("citationCount", "")

        authorships = hit.get("creators", [])                        
        for authorship in authorships:
            _author = Author()
            _author.additionalType = 'Person'
            _author.name = authorship.get("givenName", "") + " " + authorship.get("familyName", "")

            # look if there is an ORCID identifier
            _authorIdentifiers = authorship.get('nameIdentifiers', [])
            for _authorIdentifier in _authorIdentifiers:
                scheme = _authorIdentifier.get('nameIdentifierScheme', '')
                if scheme == 'ORCID' and _authorIdentifier.get('nameIdentifier'):
                    _author.identifier = _authorIdentifier.get('nameIdentifier')

            author_source = thing(
                name=source,
                identifier=_author.identifier,
            )

            _author.source.append(author_source)
            publication.author.append(_author)
        
        _source = thing()
        _source.name = source
        _source.identifier = publication.identifier
        _source.url = publication.url                                          
        publication.source.append(_source)

        return publication


    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        unfiltered_publications = [self.map_hit(hit['attributes']) for hit in hits]

        # DataCite often returns duplicate results!
        # these have the exact same information, and only differ in the DOI suffix (e.g., 10.5281/zenodo.17713041 vs 10.5281/zenodo.17713042)
        # here we remove duplicates based on the title
        titles = set()
        publications = []
        for pub in unfiltered_publications:
            if pub.name not in titles:
                titles.add(pub.name)
                publications.append(pub)

        results['publications'] = publications
    
    def get_publication(self, doi: str) -> Article | None:
        """
        Fetch a single publication by its DOI and map it to an Article object.
        """
        url = app.config['DATA_SOURCES'][source].get('get-publication-endpoint', '') + doi

        headers = {'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': app.config['REQUEST_HEADER_USER_AGENT'],
                }
        
        response = requests.get(url, headers=headers, timeout=int(app.config["REQUEST_TIMEOUT"]))                

        if response.status_code == 200:
            raw = response.json()
            hit = self.extract_hits(raw)  # this directly returns the hit, not a list!
            publication = self.map_hit(hit['attributes'])
            return publication
        else:
            utils.log_event(type="error", message=f"{source} - Get Publication response status code: {str(response.status_code)} (Requesting URL: {url})")            
            return None

def search(source_name: str, search_term: str, results: dict, failed_sources: list):
    DataCite().search(source_name, search_term, results, failed_sources)

def get_publication(source, doi, source_id, publications) -> None:
    
    source = DataCite()

    publication = source.get_publication(doi)
    if publication:
        publications.append(publication)