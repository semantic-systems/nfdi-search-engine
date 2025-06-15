from objects import thing, Article, Author, Dataset, Person
from sources import data_retriever
import utils
from main import app

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)    

    total_hits = len(search_result)

    if int(total_hits) > 0:
        utils.log_event(type="info", message=f"{source} - {total_hits} records matched")   

        for hit in search_result:

            dataset = map_entry_to_dataset(hit)
            results['resources'].append(dataset)

def map_entry_to_dataset(record) -> Dataset:

    dataset = Dataset()     # thing -> CreateWork -> Dataset

    dataset.identifier = record.get("id", "")
    dataset.name = record.get("id", "")
    dataset.additionalType = "DATASET"
    dataset.url = "https://huggingface.co/datasets/" + record.get("id", "")
    dataset.description = utils.remove_html_tags(record.get("description", ""))
    dataset.abstract = dataset.description
    dataset.license = record.get("license", {}).get("id", "")
    dataset.datePublished = record.get("createdAt", "")
    dataset.dateModified = record.get("lastModified", "")

    # much metadata is contained in the tags
    tags = record.get("tags", [])

    dataset.inLanguage = [t.split("language:")[1] for t in tags if t.startswith("language:")]
    dataset.genre = ", ".join(t.split("task_categories:")[1] for t in tags if t.startswith("task_categories:"))
    dataset.encodingFormat = ", ".join(t.split("format:")[1] for t in tags if t.startswith("format:"))
    dataset.countryOfOrigin = next((t.split("region:")[1] for t in tags if t.startswith("region:")), "")
    dataset.keywords = tags

    dataset.license = next((t.split("license:")[1] for t in tags if t.startswith("license:")), "")

    dataset.creativeWorkStatus = (
        "disabled" if record.get("disabled")
        else "private" if record.get("private")
        else "gated" if record.get("gated")
        else "public"
    )

    if record.get("author"):
        dataset.author = [Author(name=record["author"])]
        dataset.publisher = dataset.author[0].name if dataset.author else ""

    _source = thing()
    _source.name = 'Huggingface - Datasets'
    _source.originalSource = dataset.publisher
    _source.identifier = dataset.identifier
    _source.url = dataset.url
    dataset.source.append(_source)

    return dataset

@utils.handle_exceptions
def get_resource(source: str, source_id: str, doi: str):
    """
    Retrieve detailed information for the dataset. 

    :param source: source label for the data source; in this case its huggingface
    :param source_id: the primay identifier in the source records
    :param doi: digital identifier for the dataset

    :return: dataset
    """

    print(f"{source=}")
    print(f"{source_id=}")
    print(f"{doi=}")

    base_url = 'https://huggingface.co/api/datasets/'
    search_result = data_retriever.retrieve_object(source=source,
                                                    base_url=base_url,
                                                    identifier=doi)
    
    if search_result:
        dataset = map_entry_to_dataset(search_result)
        utils.log_event(type="info", message=f"{source} - retrieved dataset details")
        return dataset
    else:
        utils.log_event(type="error", message=f"{source} - failed to retrieve dataset details")
        return None
    