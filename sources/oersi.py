from nfdi_search_engine.common.models.objects import thing, Article, Author
from sources import data_retriever
from typing import Iterable, Dict, Any, List
from config import Config

from sources.base import BaseSource
from nfdi_search_engine.common.formatting import remove_html_tags


class OERSI(BaseSource):

    SOURCE = 'OERSI'

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(
            base_url=Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', ''),
            search_term=search_term,
        )

        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        return raw['hits']['hits']

    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        hit_source = hit.get('_source', {})

        publication = Article()
        publication.name = hit_source.get("name", "")
        publication.url = hit_source.get("id", "")
        publication.identifier = hit_source.get("id", "").replace("https://doi.org/", "")
        publication.datePublished = hit_source.get("datePublished", "")
        publication.license = hit_source.get("license", {}).get("id", "")

        publication.description = remove_html_tags(hit_source.get("description", ""))
        publication.abstract = publication.description
        # every object is categorized as 'learning resource' which is vague. not sure whether this information should be used.
        publication.additionalType = ','.join(hit_source.get("type", []))

        publishers = hit_source.get("publisher", [])
        if len(publishers) > 0:
            publication.publication = publishers[0].get("name", "")

        for author in hit_source.get("creator", []):
            if author['type'] == 'Person':
                _author = Author()
                _author.additionalType = 'Person'
                _author.name = author.get("name", "")
                _author.identifier = author.get("id", "").replace('https://orcid.org/', '')
                author_source = thing(
                    name=self.SOURCE,
                    identifier=_author.identifier,
                )
                _author.source.append(author_source)
                publication.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("_id", "")
        _source.url = "https://oersi.org/resources/" + hit.get("_id", "")
        publication.source.append(_source)

        # information only limited to this source
        publication.image = hit_source.get("image", "")
        keywords = hit_source.get("keywords", None)
        if keywords:
            for keyword in keywords:
                publication.keywords.append(keyword)

        languages = hit_source.get("inLanguage", None)
        if languages:
            for language in languages:
                publication.inLanguage.append(language)

        encodings = hit_source.get("encoding", None)
        if encodings:
            for encoding in encodings:
                publication.encoding_contentUrl = encoding.get("contentUrl", "")
                publication.encodingFormat = encoding.get("encodingFormat", "")

        return publication

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """

        raw = self.fetch(search_term)
        hits = self.extract_hits(raw)

        for hit in hits:
            publication = self.map_hit(hit)

            if publication.identifier != "":
                results['publications'].append(publication)
            else:
                results['others'].append(publication)


def search(search_term: str, results, tracking=None):
    """
    Entrypoint to search CORDIS publications.
    """
    return OERSI(tracking).search(search_term, results)
