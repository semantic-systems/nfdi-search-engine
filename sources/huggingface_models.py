"""Simple wrappers for Hugging Face model search/detail retrieval that mirror
Dataset‑handlers style (single mapping helper + thin search/get functions).
"""
from __future__ import annotations

from objects import thing, CreativeWork, Author
from sources import data_retriever
import utils
from main import app


def map_entry_to_model(record) -> CreativeWork:
    """Convert a single Huggingface model record into a :class:`CreativeWork`."""

    model = CreativeWork()  # thing -> CreativeWork

    model.identifier = record.get("id", "") or record.get("modelId", "")
    model.name = record.get("modelId", "") or record.get("id", "")
    model.additionalType = "MODEL"
    model.url = f"https://huggingface.co/{model.name}"

    model.description = utils.remove_html_tags(record.get("description", ""))
    model.abstract = model.description
    model.dateCreated = record.get("createdAt", "")
    model.datePublished = model.dateCreated
    model.dateModified = record.get("lastModified", "")

    model.rankScore = float(record.get("trendingScore", 0))

    tags = record.get("tags", [])
    model.genre = record.get("pipeline_tag", "")
    model.encodingFormat = record.get("library_name", "")
    model.countryOfOrigin = next((t.split("region:")[1] for t in tags if t.startswith("region:")), "")
    model.keywords = tags
    model.license = next((t.split("license:")[1] for t in tags if t.startswith("license:")), "")

    model.creativeWorkStatus = (
        "disabled" if record.get("disabled")
        else "private" if record.get("private")
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


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """Populate *results['resources']* with models matching *search_term*."""
    search_result = data_retriever.retrieve_data(
        source=source,
        base_url=app.config["DATA_SOURCES"][source].get("search-endpoint", ""),
        search_term=search_term,
        failed_sources=failed_sources,
    )

    total_hits = len(search_result)
    if total_hits == 0:
        return

    utils.log_event(type="info", message=f"{source} - {total_hits} records matched")

    for hit in search_result:
        model = map_entry_to_model(hit)
        results["resources"].append(model)


@utils.handle_exceptions
def get_resource(source: str, source_id: str, identifier: str):
    """Retrieve full details for a single model and return a :class:`CreativeWork`."""
    base_url = "https://huggingface.co/api/models/"
    search_result = data_retriever.retrieve_object(
        source=source,
        base_url=base_url,
        identifier=identifier,
    )

    if search_result:
        model = map_entry_to_model(search_result)
        utils.log_event(type="info", message=f"{source} - retrieved model details")
        return model
    else:
        utils.log_event(type="error", message=f"{source} - failed to retrieve model details")
        return None
