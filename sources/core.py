from objects import thing, Article, Author, Organization
from sources import data_retriever
from config import Config
import utils
import requests
from main import app

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):

    # we cannot use data_retriever.retrieve_data here because we need to send the request with an API key in the header
    # learn more: https://api.core.ac.uk/docs/v3#tag/Search
    limit = Config.NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT
    api_url = f'https://api.core.ac.uk/v3/search/works/?limit={limit}&q={search_term}&_exists_:doi'
    headers = {"Authorization":"Bearer " + Config.CORE_API_KEY}

    # send the request
    r = requests.get(api_url, headers=headers)
    r.raise_for_status()
    search_results = r.json()

    hits = search_results['results']
    total_hits = search_results['totalHits']
    total_results = len(hits)

    utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {total_results}") 
    print(f"{source} - {total_hits} records matched; pulled top {total_results}")

    for i, hit in enumerate(hits):
        digitalObj = map_digital_obj(source, hit)

        # we only create a result object if we found a DOI, otherwise None
        if digitalObj:
            results['publications'].append(digitalObj)   

@utils.handle_exceptions
def map_digital_obj(source: str, hit: dict) -> Article:

    publication = Article() 
    publication.additionalType = hit.get("documentType", "")
    publication.name = hit.get("title", "")

    # go through the links and find the one with type: display
    links = hit.get("links", {})
    for link in links:
        if link.get("type", "") == "display":
            publication.url = link.get("url", "")
            break
    
    publication.encoding_contentUrl = hit.get("downloadUrl", "")

    # publications may not always have a DOI!
    # if we don't find one, we do NOT create a result object for the hit
    if not hit.get("doi", None):
        print("No DOI found for publication:", publication.name)
        return None

    publication.identifier = hit.get("doi", "")
    publication.datePublished = hit.get("publishedDate", "")
    publication.inLanguage.append(hit.get("language", {}).get("code", ""))

    # abstracts may also be empty
    abstract = hit.get("abstract", "")
    if not abstract:
        abstract = ""

    publication.description = utils.remove_html_tags(abstract)
    publication.abstract = publication.description

    publication.citationCount = hit.get("citationCount", "")

    if hit.get("publisher", ""):
        _publisher = Organization()
        _publisher.name = hit.get("publisher", "")
        publication.publisher = _publisher

    authors = hit.get("authors", [])
    for author in authors:
        _author = Author()
        _author.additionalType = 'Person'
        _author.name = author.get("name", "")
        publication.author.append(_author)
    
    _source = thing()
    _source.name = source
    _source.identifier = publication.identifier
    _source.url = publication.url
    publication.source.append(_source)

    return publication