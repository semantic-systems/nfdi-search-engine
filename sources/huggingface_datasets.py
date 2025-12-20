from typing import Union, Dict, Any, List, Iterable

import utils
from config import Config
from sources.base import BaseSource
from sources import data_retriever
from objects import thing, Article, Author, Dataset, Person


class HuggingFaceDatasets(BaseSource):
    SOURCE = "Huggingface - Datasets"
    SEARCH_ENDPOINT = Config.DATA_SOURCES[SOURCE].get('search-endpoint', '')
    RESOURCE_ENDPOINT = Config.DATA_SOURCES[SOURCE].get("get-resource-endpoint", "")

    def fetch(self, search_term: str, failed_sources: list = []) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        return data_retriever.retrieve_data(
            source=self.SOURCE,
            base_url=self.SEARCH_ENDPOINT,
            search_term=search_term,
            failed_sources=failed_sources,
        ) or {}

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        return raw

    def map_hit(self, source_name: str, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        dataset = Dataset()     # thing -> CreateWork -> Dataset

        dataset.identifier = hit.get("id", "")
        dataset.name = hit.get("id", "")
        dataset.additionalType = "DATASET"
        dataset.url = "https://huggingface.co/datasets/" + hit.get("id", "")
        dataset.description = utils.remove_html_tags(hit.get("description", ""))
        dataset.abstract = dataset.description
        dataset.license = hit.get("license", {}).get("id", "")
        dataset.datePublished = hit.get("createdAt", "")
        dataset.dateModified = hit.get("lastModified", "")

        # much metadata is contained in the tags
        tags = hit.get("tags", [])

        dataset.inLanguage = [t.split("language:")[1] for t in tags if t.startswith("language:")]
        dataset.genre = ", ".join(t.split("task_categories:")[1] for t in tags if t.startswith("task_categories:"))
        dataset.encodingFormat = ", ".join(t.split("format:")[1] for t in tags if t.startswith("format:"))
        dataset.countryOfOrigin = next((t.split("region:")[1] for t in tags if t.startswith("region:")), "")
        dataset.keywords = tags

        dataset.license = next((t.split("license:")[1] for t in tags if t.startswith("license:")), "")

        dataset.creativeWorkStatus = (
            "disabled" if hit.get("disabled")
            else "private" if hit.get("private")
            else "gated" if hit.get("gated")
            else "public"
        )

        if hit.get("author"):
            dataset.author = [Author(name=hit["author"])]
            dataset.publisher = dataset.author[0].name if dataset.author else ""

        _source = thing()
        _source.name = source_name
        _source.originalSource = dataset.publisher
        _source.identifier = dataset.identifier
        _source.url = dataset.url
        dataset.source.append(_source)

        return dataset

    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        search_result = self.fetch(search_term, failed_sources)

        total_hits = len(search_result)
        if int(total_hits) > 0:
            utils.log_event(type="info", message=f"{self.SOURCE} - {total_hits} records matched")

            for hit in search_result:
                dataset = self.map_hit(self.SOURCE, hit)
                results['resources'].append(dataset)

    def get_resource(self, doi: str) -> Dataset | None:
        search_result = data_retriever.retrieve_object(
            source=self.SOURCE,
            base_url=self.RESOURCE_ENDPOINT,
            identifier=doi,
            quote=False,
        )
        if search_result:
            dataset = self.map_hit(self.SOURCE, search_result)
            utils.log_event(type="info", message=f"{self.SOURCE} - retrieved dataset details")
            return dataset
        else:
            utils.log_event(type="error", message=f"{self.SOURCE} - failed to retrieve dataset details")
            return None


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources) -> None:
    """
    Entrypoint to search Huggingface Datasets.
    """
    HuggingFaceDatasets().search(source, search_term, results, failed_sources)


@utils.handle_exceptions
def get_resource(source: str, source_id: str, doi: str) -> Dataset | None:
    """
    Retrieve detailed information for the dataset. 

    :param source: source label for the data source; in this case its huggingface
    :param source_id: the primay identifier in the source records
    :param doi: digital identifier for the dataset

    :return: dataset
    """
    return HuggingFaceDatasets().get_resource(doi)
