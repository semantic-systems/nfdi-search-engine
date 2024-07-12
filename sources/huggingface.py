from huggingface_hub import HfApi, ModelCard, hf_hub_url, get_hf_file_metadata


def retrieve_model_tags(model):
    tags = set(model.tags)
    if model.pipeline_tag:
        tags.add(model.pipeline_tag)
    if hasattr(model, 'cardData') and 'tags' in model.cardData:
        card_tags = model.cardData['tags']
        if isinstance(card_tags, list):
            tags.update(card_tags)
        else:
            tags.add(card_tags)
    return list(filter(None, tags))


def find_model_size(modelId):
    try:
        metadata = get_hf_file_metadata(hf_hub_url(repo_id=modelId, filename="pytorch_model.bin"))
        return metadata.size
    except Exception as e:
        print(f"Error finding model size for {modelId}: {e}")
        return None


def retrieve_model_datasets(model):
    if hasattr(model, 'cardData') and 'datasets' in model.cardData:
        datasets = model.cardData["datasets"]
        return datasets if isinstance(datasets, list) else [datasets]
    return ['']


def find_datasets_size(datasets, api):
    total_size = 0
    for dataset in datasets:
        try:
            dataset_info = api.dataset_info(dataset).cardData["dataset_info"]["dataset_size"]
            total_size += dataset_info
        except Exception as e:
            print(f"Error finding dataset size for {dataset}: {e}")
            continue
    return total_size


def get_modelcard_text(model):
    try:
        return ModelCard.load(model.modelId).text
    except Exception as e:
        print(f"Error loading model card text for {model.modelId}: {e}")
        return None


def search_models(api, search_term, limit=10):
    results = list(api.list_models(search=search_term, cardData=True, full=True, fetch_config=True))

    if not results:
        print(f"No models found for search term '{search_term}'.")
        return []
    output_list = []

    for model in results[:limit]:
        try:
            tags = retrieve_model_tags(model)
            datasets = retrieve_model_datasets(model)
            library_name = getattr(model, 'library_name', None)
            model_card_text = get_modelcard_text(model)
            # model_card_text = get_model_card_text(api, model.modelId)
            model_size = find_model_size(model.modelId)
            # model_size = lambda modelId: next((metadata.size for metadata in [
            #     get_hf_file_metadata(hf_hub_url(repo_id=modelId, filename="pytorch_model.bin"))] if metadata), None)
            datasets_size = find_datasets_size(datasets, api)

            output_list.append({
                'modelId': model.modelId,
                'tags': tags,
                'datasets': datasets,
                'downloads': model.downloads,
                'likes': model.likes,
                'library_name': library_name,
                'lastModified': model.lastModified,
                'modelcard_text': model_card_text,
                'model_size': model_size,
                'datasets_size': datasets_size
            })
        except Exception as e:
            print(f'{model.modelId} could not be processed: {e}')
            continue

    return output_list


def search_datasets(api, search_term, limit=10):
    datasets_info = []

    try:
        results = list(api.list_datasets(search=search_term))
        if not results:
            print(f"No models found for search term '{search_term}'.")
            return []
        if len(results) < limit:
            limit = len(results)
        for result in results[:limit]:
            description_text = getattr(result, "description", None)
            card_text = getattr(result, "cardData", None)
            if description_text:
                description_text = description_text.strip()
                # description_text = re.sub(r"[\n\t]+", "\n", description_text)
            dataset_info = {
                "id": getattr(result, "id", None),
                "description": description_text,
                "downloads": getattr(result, "downloads", None),
                "tags": getattr(result, "tags", None),
                "cardData": card_text,
            }
            datasets_info.append(dataset_info)
    except Exception as e:
        print(f"An error occurred: {e}")

    return datasets_info


if __name__ == "__main__":
    search_term = "hotpot"
    api = HfApi()
    print(search_models(api, search_term))
    print(search_datasets(api, search_term))