from objects import thing, Project, Author
from sources import data_retriever
from typing import Iterable, Dict, Any, List
import utils
from main import app

from sources.base import BaseSource

class CORDIS(BaseSource):

    SOURCE = 'CORDIS'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_term = f"({search_term})"
        search_result = data_retriever.retrieve_data(source=self.SOURCE, 
                                                    base_url=app.config['DATA_SOURCES'][self.SOURCE].get('search-endpoint', ''),
                                                    search_term=search_term,
                                                    failed_sources=failed_sources) 
        total_records_found = search_result.get('result', {}).get('header', {}).get('totalHits', 0)
        total_records_pulled = search_result.get('result', {}).get('header', {}).get('numHits', 0)
        utils.log_event(type="info", message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_records_pulled}")   

        return search_result
    

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        return raw.get('hits', {}).get('hit', [])
    

    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """

        if isinstance(hit, dict):
            projectNode = hit.get('project', {})
            type = projectNode.get('contenttype', '')

            if type == "project":
                project = Project()
                project.identifier = projectNode.get('identifiers', {}).get('grantDoi', '')
                project.name = projectNode.get('title', '')
                project.alternateName = projectNode.get('acronym', '')
                project.url = f"https://cordis.europa.eu/project/id/{projectNode.get('id', '')}"
                project.dateStart = projectNode.get('startDate', '')
                project.dateEnd = projectNode.get('endDate', '')
                project.duration = projectNode.get('duration', '')                
                project.datePublished = projectNode.get('ecSignatureDate', '')                
                project.description = projectNode.get("objective", '')
                project.status = projectNode.get("status", '')
                project.totalCost = "{:,.2f}".format(float(projectNode.get('totalCost', '')))
                project.eu_contribution = "{:,.0f}".format(float(projectNode.get('ecMaxContribution', '')))

                keywords = projectNode.get("keywords", None)
                if keywords:
                    for keyword in keywords:
                        project.keywords.append(keyword)

                languages = projectNode.get("language", None)
                if languages:
                    if isinstance(languages, list):
                        # If languages is a list, add each language to project.inLanguage
                        for language in languages:
                            project.inLanguage.append(language)
                    else:
                        # If languages is a single string, directly append it to project.inLanguage
                        project.inLanguage.append(languages)                

                _source = thing()
                _source.name = self.SOURCE
                _source.identifier = projectNode.get('id', '')
                _source.url = project.url                        
                project.source.append(_source)

                return project
            
        return None
    

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        for hit in hits:
            project = self.map_hit(hit)

            if project:
                results['projects'].append(project)

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search CORDIS publications.
    """
    CORDIS().search(source, search_term, results, failed_sources)