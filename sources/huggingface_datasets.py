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

            dataset = Dataset()     # thing -> CreateWork -> Dataset

            # dataset.identifier = hit.get("_id", "")
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
            _source.name = 'Huggingface - Dataset'
            _source.originalSource = dataset.publisher
            _source.identifier = dataset.identifier
            _source.url = dataset.url
            dataset.source.append(_source)
            
            results['resources'].append(dataset)