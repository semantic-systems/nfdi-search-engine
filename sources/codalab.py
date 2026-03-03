from typing import Dict, Any, Iterable, List

import utils
from config import Config
from sources.base import BaseSource
from sources import data_retriever
from objects import Dataset, Person, Author, thing


class Codalab(BaseSource):
    """
    Codalab adapter: fetches dataset bundles from worksheets.codalab.org
    and maps them to Dataset objects.
    """

    SOURCE = "CODALAB"
    SEARCH_ENDPOINT = Config.DATA_SOURCES[SOURCE].get("search-endpoint", "")
    RESOURCE_ENDPOINT = Config.DATA_SOURCES[SOURCE].get("get-resource-endpoint", "")

    def fetch(self, search_term: str, failed_sources: list = []) -> Dict[str, Any]:
        """
        Fetch raw JSON from Codalab bundles API.
        """
        return data_retriever.retrieve_data(
            source=self.SOURCE,
            base_url=self.SEARCH_ENDPOINT,
            search_term=search_term,
            failed_sources=failed_sources,
        ) or {}

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract bundle hits from JSON API response.
        """
        if not raw:
            return []

        bundles = raw.get("data", [])
        self._included = raw.get("included", [])

        hits = [b for b in bundles if b.get("type") == "bundles"]

        utils.log_event(
            type="info",
            message=f"{self.SOURCE} - {len(hits)} bundle(s) matched",
        )

        return hits

    def _resolve_author(self, bundle: Dict[str, Any]) -> List[Author]:
        """
        Resolve owner relationship to Author object.
        """
        authors = []

        owner_rel = bundle.get("relationships", {}).get("owner", {}).get("data")
        if not owner_rel:
            return authors

        owner_id = owner_rel.get("id")
        included = getattr(self, "_included", [])

        for entity in included:
            if entity.get("id") != owner_id:
                continue

            attrs = entity.get("attributes", {})
            author = Author()
            author.additionalType = "Person"
            author.identifier = owner_id

            author.name = (
                attrs.get("user_name")
                or attrs.get("first_name")
                or attrs.get("last_name")
                or ""
            )

            author_source = thing(
                name=self.SOURCE,
                identifier=owner_id,
            )
            author.source.append(author_source)

            authors.append(author)
            break

        return authors

    def map_hit(self, source_name: str, hit: Dict[str, Any]) -> Dataset:
        """
        Map Codalab bundle to Dataset object.
        """
        attrs = hit.get("attributes", {})
        metadata = attrs.get("metadata", {})

        dataset = Dataset()

        dataset.identifier = hit.get("id", "")
        dataset.name = metadata.get("name", "")
        dataset.additionalType = "DATASET"

        dataset.description = metadata.get("description", "")
        dataset.abstract = dataset.description
        dataset.license = metadata.get("license", "")

        created_ts = metadata.get("created")
        if created_ts:
            dataset.datePublished = utils.parse_date(created_ts)

        dataset.url = f"https://worksheets.codalab.org/bundles/{dataset.identifier}"

        dataset.author = self._resolve_author(hit)

        _source = thing()
        _source.name = source_name
        _source.identifier = dataset.identifier
        _source.url = dataset.url
        dataset.source.append(_source)

        return dataset

    def search(
        self,
        source_name: str,
        search_term: str,
        results: dict,
        failed_sources: list,
    ) -> None:
        """
        Search Codalab and append mapped datasets to results["resources"].
        """
        raw = self.fetch(search_term, failed_sources)

        if not raw:
            return

        hits = self.extract_hits(raw)

        for hit in hits:
            dataset = self.map_hit(self.SOURCE, hit)
            results["resources"].append(dataset)

    def get_resource(self, identifier: str) -> Dataset | None:
        """
        Retrieve a single Codalab bundle by UUID.
        """
        raw = data_retriever.retrieve_object(
            source=self.SOURCE,
            base_url=self.RESOURCE_ENDPOINT,
            identifier=identifier,
            quote=False,
        )

        if not raw:
            utils.log_event(
                type="error",
                message=f"{self.SOURCE} - failed to retrieve dataset details",
            )
            return None

        dataset = self.map_hit(self.SOURCE, raw.get("data", {}))

        utils.log_event(
            type="info",
            message=f"{self.SOURCE} - retrieved dataset details",
        )

        return dataset


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources) -> None:
    Codalab().search(source, search_term, results, failed_sources)


@utils.handle_exceptions
def get_resource(source: str, source_id: str, doi: str) -> Dataset | None:
    return Codalab().get_resource(source_id)