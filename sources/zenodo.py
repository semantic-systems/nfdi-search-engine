from objects import thing, Article, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
from sources import data_retriever
from config import Config
from sources.base import BaseSource
from typing import Union, Dict, Any, List, Iterable
import utils
from nfdi_search_engine.common.formatting import remove_html_tags

class ZENODO(BaseSource):
    """
        Implements the BaseSource interface for Zenodo.
    """
    SOURCE = "ZENODO"

    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        search_result = data_retriever.retrieve_data(source=self.SOURCE,
                                                     base_url=Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', ''),
                                                     search_term=search_term,
                                                     failed_sources=failed_sources)
        return search_result


    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        total_records_found = raw.get("hits", {}).get("total", 0)
        hits = raw.get("hits", {}).get("hits", [])
        total_hits = len(hits)
        self.log_event(type="info",
                        message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}")
        if int(total_hits) > 0:
            return hits
        return []

    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]) -> Union[Article, CreativeWork, Dataset, VideoObject, ImageObject, LearningResource, SoftwareApplication]:
        metadata = hit.get('metadata', {})
        resource_type = metadata.get('resource_type', {}).get('type', 'OTHER').upper()

        if resource_type == 'PUBLICATION':
            digitalObj = Article()
        elif resource_type in ['PRESENTATION', 'POSTER']:
            digitalObj = CreativeWork()
        elif resource_type == 'DATASET':
            digitalObj = Dataset()
        elif resource_type == 'VIDEO':
            digitalObj = VideoObject()
        elif resource_type == 'IMAGE':
            digitalObj = ImageObject()
        elif resource_type == 'LESSON':
            digitalObj = LearningResource()
        elif resource_type == 'SOFTWARE':
            digitalObj = SoftwareApplication()
        elif resource_type == 'OTHER':
            digitalObj = CreativeWork()
        else:
            self.log_event(type="info", message=f"{self.SOURCE} - Resource type not defined: {resource_type}")
            digitalObj = CreativeWork()

        digitalObj.additionalType = resource_type
        digitalObj.identifier = hit.get('doi', '')
        digitalObj.name = hit.get('title', '')
        digitalObj.url = hit.get('links', {}).get('self', '')

        digitalObj.description = remove_html_tags(metadata.get('description', ''))

        keywords = metadata.get('keywords', [])
        if isinstance(keywords, list):
            for keyword in keywords:
                digitalObj.keywords.append(keyword)

        language = metadata.get('language', '')
        digitalObj.inLanguage.append(language)

        digitalObj.datePublished = metadata.get('publication_date', '')
        digitalObj.license = metadata.get('license', {}).get('id', '')

        authors = metadata.get("creators", [])
        for author in authors:
            _author = Author()
            _author.additionalType = 'Person'
            _author.name = author.get("name", "")
            _author.identifier = author.get("orcid", "")
            _author.affiliation = author.get("affiliation", "")
            author_source = thing(
                name=self.SOURCE,
                identifier=_author.identifier,
            )
            _author.source.append(author_source)
            digitalObj.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("id", "")
        _source.url = hit.get('links', {}).get('self_html', '')
        digitalObj.source.append(_source)

        if resource_type.upper() == 'PUBLICATION':
            digitalObj.abstract = digitalObj.description

            files = hit.get('files', [])
            for file in files:
                if file.get("key", "").endswith(".pdf"):
                    digitalObj.encoding_contentUrl = file.get("links", {}).get("self", "")

        return digitalObj

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)
        for hit in hits:
            metadata = hit.get('metadata', {})
            resource_type = metadata.get('resource_type', {}).get('type','OTHER').upper()
            digitalObj = self.map_hit(hit)

            if resource_type.upper() == 'PUBLICATION':
                results['publications'].append(digitalObj)
            elif resource_type.upper() in ['DATASET', 'SOFTWARE']:
                results['resources'].append(digitalObj)
            else: # 'PRESENTATION', 'POSTER', 'VIDEO', 'IMAGE', 'LESSON', OTHERS
                results['others'].append(digitalObj)


def search(source_name: str, search_term: str, results: dict, failed_sources: list, tracking=None):
    ZENODO(tracking).search(source_name, search_term, results, failed_sources)
