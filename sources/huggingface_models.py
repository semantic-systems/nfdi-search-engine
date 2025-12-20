from typing import Union, Dict, Any, List, Iterable

import utils
from config import Config
from sources import data_retriever
from sources.base import BaseSource
from objects import thing, CreativeWork, Author

import requests


class HuggingFaceModels(BaseSource):
    SOURCE = "Huggingface - Models"
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

    def map_hit(self, source_name: str, hit: Dict[str, Any], request_readme: bool = False):
        """
        Convert a single Huggingface model record into a `CreativeWork` object.
        """
        model = CreativeWork()  # thing -> CreativeWork

        model.identifier = hit.get("id", "") or hit.get("modelId", "")
        model.name = hit.get("modelId", "") or hit.get("id", "")
        model.additionalType = "MODEL"
        model.url = f"https://huggingface.co/{model.name}"

        # model descriptions are usually contained in a README file, which we will request separately
        if request_readme:
            readme_url = f"https://huggingface.co/{model.name}/raw/main/README.md"
            try:
                response = requests.get(readme_url, timeout=5)
                if response.status_code == 200:
                    model.description = utils.remove_html_tags(response.text)
                else:
                    model.description = utils.remove_html_tags(hit.get("description", ""))
            except requests.RequestException:
                model.description = utils.remove_html_tags(hit.get("description", ""))
        else:
            model.description = utils.remove_html_tags(hit.get("description", ""))

        model.abstract = model.description
        model.dateCreated = hit.get("createdAt", "")
        model.datePublished = model.dateCreated
        model.dateModified = hit.get("lastModified", "")

        model.rankScore = float(hit.get("trendingScore", 0))

        tags = hit.get("tags", [])
        model.genre = hit.get("pipeline_tag", "")
        model.encodingFormat = hit.get("library_name", "")
        model.countryOfOrigin = next((t.split("region:")[1] for t in tags if t.startswith("region:")), "")
        model.keywords = tags
        model.license = next((t.split("license:")[1] for t in tags if t.startswith("license:")), "")

        model.creativeWorkStatus = (
            "disabled" if hit.get("disabled")
            else "private" if hit.get("private")
            else "public"
        )

        owner = model.name.split("/")[0] if model.name else ""
        if owner:
            model.author = [Author(name=owner)]
            model.publisher = owner

        model.encoding_contentUrl = model.url

        _src = thing()
        _src.name = "Huggingface - Models"
        _src.originalSource = model.publisher
        _src.identifier = model.identifier
        _src.url = model.url
        model.source.append(_src)

        return model

    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list, request_readme: bool = False) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        search_result = self.fetch(search_term, failed_sources)

        total_hits = len(search_result)
        if int(total_hits) > 0:
            utils.log_event(type="info", message=f"{self.SOURCE} - {total_hits} records matched")

            for hit in search_result:
                model = self.map_hit(self.SOURCE, hit, request_readme)
                results['resources'].append(model)

    def get_resource(self, doi: str, request_readme: bool = False) -> CreativeWork | None:
        search_result = data_retriever.retrieve_object(
            source=self.SOURCE,
            base_url=self.RESOURCE_ENDPOINT,
            identifier=doi,
            quote=False,
        )
        if search_result:
            model = self.map_hit(self.SOURCE, search_result, request_readme)
            utils.log_event(type="info", message=f"{self.SOURCE} - retrieved model details")
            return model
        else:
            utils.log_event(type="error", message=f"{self.SOURCE} - failed to retrieve model details")
            return None


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources) -> None:
    """
    Entrypoint to search Huggingface Models.
    """
    HuggingFaceModels().search(source, search_term, results, failed_sources)


@utils.handle_exceptions
def get_resource(source: str, source_id: str, doi: str) -> CreativeWork | None:
    """
    Retrieve detailed information for the model. 

    :param source: source label for the data source; in this case its huggingface
    :param source_id: the primay identifier in the source records
    :param doi: digital identifier for the model

    :return: CreativeWork
    """
    return HuggingFaceModels().get_resource(doi)
