from objects import thing, CreativeWork, Author, Dataset, Person
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

            model = CreativeWork()     # thing -> CreativeWork

            # model.identifier = hit.get("_id", "")
            model.name = hit.get("modelId", "") or hit.get("id", "")
            model.additionalType = "MODEL"
            model.url = "https://huggingface.co/" + model.name
            model.dateCreated = hit.get("createdAt", "")
            model.datePublished = model.dateCreated
            model.rankScore = float(hit.get("trendingScore", 0))

            tags = hit.get("tags", [])

            # model.inLanguage = [t for t in tags if len(t) <= 3 and t.isalpha()]
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

            owner = model.name.split("/")[0]
            if owner:
                model.author = [Author(name=owner)]
                model.publisher = owner

            model.encoding_contentUrl = model.url

            _source = thing()
            _source.name = 'Huggingface - Model'
            _source.originalSource = model.publisher
            _source.identifier = model.identifier
            _source.url = model.url
            model.source.append(_source)

            results['resources'].append(model)
