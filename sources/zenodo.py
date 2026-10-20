from typing import Union, Dict, Any, List, Iterable

from nfdi_search_engine.common.models.objects import thing, Article, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
from sources.http_client import quote_term
from sources.base import BaseSource
from config import Config
from nfdi_search_engine.common.formatting import remove_html_tags


class ZENODO(BaseSource):
    """
        Implements the BaseSource interface for Zenodo.
    """
    SOURCE = "ZENODO"

    def fetch(self, search_term: str) -> Dict[str, Any]:
        return self.http.get_json(
            Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', '')
            + quote_term(search_term)
        )

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        total_records_found = raw.get("hits", {}).get("total", 0)
        hits = raw.get("hits", {}).get("hits", [])
        total_hits = len(hits)
        self.log_event(type="info",
                        message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}")
        if int(total_hits) > 0:
            return hits
        return []

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
        digitalObj.identifier = hit.get('doi', '') or metadata.get('doi', '')
        digitalObj.name = hit.get('title', '') or metadata.get('title', '')
        digitalObj.url = hit.get('links', {}).get('self', '')

        digitalObj.description = remove_html_tags(metadata.get('description', ''))
        digitalObj.abstract = digitalObj.description

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
            files = hit.get('files', [])
            for file in files:
                if file.get("key", "").endswith(".pdf"):
                    digitalObj.encoding_contentUrl = file.get("links", {}).get("self", "")

        return digitalObj

    def search(self, search_term: str, results: dict) -> None:
        raw = self.fetch(search_term)
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

    def get_resource(self, identifier: str) -> Union[CreativeWork, Dataset, SoftwareApplication, None]:
        """
        Retrieve detailed information for a single Zenodo resource.
        The identifier is the Zenodo record id from source metadata.
        """
        search_result = self.http.get_json(
            Config.DATA_SOURCES[self.SOURCE].get('get-resource-endpoint', '')
            + identifier
        )
        if not search_result:
            self.log_event(type="error", message=f"{self.SOURCE} - failed to retrieve resource details")
            return None

        digital_obj = self.map_hit(search_result)
        if digital_obj.additionalType.upper() in ['DATASET', 'SOFTWARE']:
            self.log_event(type="info", message=f"{self.SOURCE} - retrieved resource details")
            return digital_obj

        self.log_event(
            type="error",
            message=f"{self.SOURCE} - detail record is not a resource type: {digital_obj.additionalType}",
        )
        return None


def search(search_term: str, results: dict, tracking=None):
    ZENODO(tracking).search(search_term, results)


def get_resource(doi: str, tracking=None) -> Union[CreativeWork, Dataset, SoftwareApplication, None]:
    return ZENODO(tracking).get_resource(doi)
