import re
from typing import Iterable, Dict, Any, List

from nfdi_search_engine.common.models.objects import thing, Article, Author, Dataset
from sources import data_retriever
from sources.base import BaseSource
from config import Config
import requests

from nfdi_search_engine.common.dates import parse_date
from nfdi_search_engine.common.formatting import remove_html_tags


class Resodate(BaseSource):
    """
    Resodate source adapter: fetches OER data from resodate.org search API,
    maps Elasticsearch-style hits to Article objects.
    """

    SOURCE = "resodate"

    def fetch(self, search_term: str) -> Dict[str, Any] | None:
        """
        Fetch raw JSON from the Resodate search API using the given search term.
        """
        search_result = data_retriever.retrieve_data(
            base_url=Config.DATA_SOURCES[self.SOURCE].get("search-endpoint", ""),
            search_term=search_term,
        )
        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw Elasticsearch-style JSON response.
        """
        if raw is None:
            return []

        hits_container = raw.get("hits", {})
        total_info = hits_container.get("total", 0)
        if isinstance(total_info, dict):
            total_hits = total_info.get("value", 0)
        else:
            total_hits = total_info

        hits = hits_container.get("hits", [])

        if int(total_hits) > 0:
            self.log_event(
                type="info",
                message=f"{self.SOURCE} - {total_hits} records matched; pulled top {len(hits)}",
            )

        return hits

    def _ensure_list(self, value) -> List:
        """
        Normalize value to a list for resilient handling of string/list fields.
        """
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def map_dataset_hit(self, hit: Dict[str, Any]) -> Dataset:
        """
        Map a single dataset hit (with _source and _id) to a Dataset object.
        """
        hit_source = hit.get("_source", {})

        dataset = Dataset()
        dataset.name = hit_source.get("name", "")
        dataset.url = "https://resodate.org/resources/" + hit.get("_id", "")
        dataset.identifier = hit_source.get("id", "")

        # description / abstract
        dataset.description = remove_html_tags(hit_source.get("description", ""))
        dataset.abstract = dataset.description

        # datePublished preference: datePublished -> mainEntityOfPage[0].dateCreated/dateModified
        date_published = hit_source.get("datePublished", "")
        if not date_published:
            main_entity = hit_source.get("mainEntityOfPage") or []
            if isinstance(main_entity, dict):
                main_entity = [main_entity]
            if main_entity:
                first_entity = main_entity[0] or {}
                date_published = (
                    first_entity.get("dateCreated")
                    or first_entity.get("dateModified")
                    or ""
                )
        if date_published:
            dataset.datePublished = parse_date(date_published)

        dataset.license = hit_source.get("license", {}).get("id", "")
        dataset.image = hit_source.get("image", "")

        # keywords and languages (string or list)
        for keyword in self._ensure_list(hit_source.get("keywords")):
            dataset.keywords.append(keyword)

        for language in self._ensure_list(hit_source.get("inLanguage")):
            dataset.inLanguage.append(language)

        # encoding: pick first with contentUrl
        encodings = hit_source.get("encoding")
        encoding_list: List[Dict[str, Any]] = []
        if isinstance(encodings, dict):
            encoding_list = [encodings]
        elif isinstance(encodings, list):
            encoding_list = encodings

        for encoding in encoding_list:
            content_url = encoding.get("contentUrl", "")
            if content_url:
                dataset.encoding_contentUrl = content_url
                dataset.encodingFormat = encoding.get("encodingFormat", "")
                break

        # creators mapped similar to publications
        for author in hit_source.get("creator", []):
            if author.get("type") == "Person":
                _author = Author()
                _author.additionalType = "Person"
                _author.name = author.get("name", "")
                _author.identifier = author.get("id", "").replace(
                    "https://orcid.org/", ""
                )
                author_source = thing(
                    name=self.SOURCE,
                    identifier=_author.identifier,
                )
                _author.source.append(author_source)
                dataset.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("_id", "")
        _source.url = dataset.url
        dataset.source.append(_source)

        return dataset

    def map_hit(self, hit: Dict[str, Any]) -> Article:
        """
        Map a single non-dataset hit (with _source and _id) to an Article from objects.py.
        """
        hit_source = hit.get("_source", {})

        publication = Article()
        publication.name = hit_source.get("name", "")
        publication.url = hit_source.get("id", "")
        publication.identifier = re.sub(
            r"^.*doi\.org/", "", hit_source.get("id", "")
        )
        publication.datePublished = hit_source.get("datePublished", "")
        if publication.datePublished:
            publication.datePublished = parse_date(publication.datePublished)
        publication.license = hit_source.get("license", {}).get("id", "")

        publication.description = remove_html_tags(
            hit_source.get("description", "")
        )
        publication.abstract = publication.description

        publishers = hit_source.get("publisher", [])
        if publishers:
            publication.publication = publishers[0].get("name", "")

        for author in hit_source.get("creator", []):
            if author.get("type") == "Person":
                _author = Author()
                _author.additionalType = "Person"
                _author.name = author.get("name", "")
                _author.identifier = author.get("id", "").replace(
                    "https://orcid.org/", ""
                )
                author_source = thing(
                    name=self.SOURCE,
                    identifier=_author.identifier,
                )
                _author.source.append(author_source)
                publication.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("_id", "")
        _source.url = "https://resodate.org/resources/" + hit.get("_id", "")
        publication.source.append(_source)

        publication.image = hit_source.get("image", "")

        # keywords and languages (string or list)
        for keyword in self._ensure_list(hit_source.get("keywords")):
            publication.keywords.append(keyword)

        for language in self._ensure_list(hit_source.get("inLanguage")):
            publication.inLanguage.append(language)

        # encoding can be missing or list/dict
        encodings = hit_source.get("encoding")
        encoding_list: List[Dict[str, Any]] = []
        if isinstance(encodings, dict):
            encoding_list = [encodings]
        elif isinstance(encodings, list):
            encoding_list = encodings

        for encoding in encoding_list:
            publication.encoding_contentUrl = encoding.get("contentUrl", "")
            publication.encodingFormat = encoding.get("encodingFormat", "")

        return publication

    def search(
        self,
        search_term: str,
        results: dict,
    ) -> None:
        """
        Fetch from Resodate, extract hits, map to Articles/Datasets, and append to results.
        """
        raw = self.fetch(search_term)
        if raw is None:
            return

        hits = self.extract_hits(raw)
        publication_count = 0
        dataset_count = 0

        for hit in hits:
            hit_source = hit.get("_source", {})
            hit_type = hit_source.get("type", [])
            type_list = self._ensure_list(hit_type)
            type_list_lower = [str(t).lower() for t in type_list]

            if "dataset" in type_list_lower:
                dataset = self.map_dataset_hit(hit)
                results["resources"].append(dataset)
                dataset_count += 1
            else:
                publication = self.map_hit(hit)
                results["publications"].append(publication)
                publication_count += 1

        self.log_event(
            type="info",
            message=(
                f"{self.SOURCE} - mapped {publication_count} publications and "
                f"{dataset_count} datasets"
            ),
        )

    def get_resource(
        self,
        doi: str,
    ) -> Dataset | None:
        """
        Fetch detailed resource metadata for a single RESODATE resource.

        Uses the RESODATE metadata index with an ids query on the ES document id.
        """
        api_url = "https://resodate.org/api/search/resource_metadata/_search"

        body = {
            "size": 1,
            "query": {
                "ids": {
                    "values": [self.SOURCE],
                }
            },
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": Config.REQUEST_HEADER_USER_AGENT,
        }

        try:
            response = requests.post(
                api_url,
                json=body,
                headers=headers,
                timeout=int(Config.REQUEST_TIMEOUT),
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            self.log_event(
                type="error",
                message=(
                    f"{self.SOURCE} - details request timed out: "
                    f"source_name={self.SOURCE}, doi={doi}"
                ),
            )
            return None
        except Exception as ex:
            self.log_event(
                type="error",
                message=(
                    f"{self.SOURCE} - error requesting details: "
                    f"source_name={self.SOURCE}, doi={doi}, "
                    f"error={str(ex)}"
                ),
            )
            return None

        try:
            data = response.json()
        except ValueError:
            self.log_event(
                type="error",
                message=(
                    f"{self.SOURCE} - invalid JSON in details response: "
                    f"source_name={self.SOURCE}, doi={doi}"
                ),
            )
            return None

        hits_container = data.get("hits", {})
        hits = hits_container.get("hits", [])

        if not hits:
            self.log_event(
                type="error",
                message=(
                    f"{self.SOURCE} - no details hit found: "
                    f"source_name={self.SOURCE}, doi={doi}"
                ),
            )
            return None

        hit = hits[0]
        dataset = self.map_dataset_hit(hit)

        self.log_event(
            type="info",
            message=(
                f"{self.SOURCE} - retrieved resource details: "
                f"source_name={self.SOURCE}, doi={doi}"
            ),
        )

        return dataset


def search(
    search_term: str,
    results: dict,
    tracking=None,
) -> None:
    """
    Entrypoint to search Resodate publications.
    """
    Resodate(tracking).search(search_term, results)


def get_resource(doi: str, tracking=None) -> Dataset | None:
    """
    Entrypoint to retrieve RESODATE resource details.
    """
    return Resodate(tracking).get_resource(doi)
