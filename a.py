import urllib.parse
import requests
import logging
import utils
import json
from sources import data_retriever
from objects import CreativeWork, Author

base_url = "https://zenodo.org/api/records?size=25&q="
doi = "r3730f562f9e::324df2bd7d05a0942f31f0fe34e2eefa"

# search_result = data_retriever.retrieve_single_object(source=source,
#                                                         base_url=
#                                                         doi=doi)

encoded_doi = urllib.parse.quote_plus(string=doi, safe='()?&=,')
url = base_url + encoded_doi
print(url)
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-Agent': utils.config["request_header_user_agent"]
}

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    response = requests.get(url, headers=headers, timeout=int(utils.config["request_timeout"]))
    logger.debug(f'Response status code: {response.status_code}')

    if response.status_code == 200:
        search_results = response.json()
        search_results = utils.clean_json(search_results)
        # print(search_result)
        search_result = search_results.get("hits", {}).get("hits", [])
        search_result = search_result[0]
        metadata = search_result.get("metadata", {})
        resource = CreativeWork()
        resource.name = metadata.get("title", "")
        resource.url = metadata.get('links', {}).get('self', '')
        resource.identifier = metadata.get("doi", "")
        resource.datePublished = metadata.get("publication_date", "")
        resource.inLanguage.append(metadata.get("language", ""))
        resource.license = metadata.get("license", "")

        resource.description = utils.remove_html_tags(metadata.get("description", ""))
        resource.abstract = resource.description

        authors = metadata.get("creators", [])
        for author in authors:
            _author = Author()
            _author.type = 'Person'
            _author.name = author.get("name", "")
            _author.identifier = author.get("orcid", "")
            _author.affiliation = author.get("affiliation", "")
            resource.author.append(_author)
        # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        print(json.dumps(search_result, indent=4))
        # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        # print( resource.name)
    else:
        logger.error(f'Failed to retrieve data: {response.status_code}')

except requests.exceptions.RequestException as e:
    logger.error(f'An error occurred: {e}')
