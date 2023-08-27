import requests
from objects import Dataset, Person, Author, Article, CreativeWork
import logging

logger = logging.getLogger('nfdi_search_engine')


def search(search_string: str, results):
    """ Obtain the results from Eudat request and handles them accordingly.

          Args:
              search_string: keyword(s) to search for
              results: search answer formatted into different data types according to Eudat resource_types
              and mapped to schema.org types.

          Returns:
                the results Object
          """
    api_url = 'https://b2share.eudat.eu/api/records/'
    result_url_start = 'https://b2share.eudat.eu/records/'
    response = requests.get(api_url, params={'q': search_string, 'size': 100, 'sort': 'mostrecent'})
    data = response.json()

    logger.debug(f'Eudat response status code: {response.status_code}')
    logger.debug(f'Eudat response headers: {response.headers}')

    if response.status_code == 200:
        try:
            hits = data.get('hits', {}).get('hits', [])
        except AttributeError:
            hits = []  # Set hits as an empty list if the 'get' operation fails due to AttributeError
        for hit in hits:
            result_id = hit["id"]
            url = result_url_start + result_id
            metadata = hit["metadata"]
            doi = metadata.get("DOI", "")
            # epic_pid = metadata.get("ePIC_PID", "")
            language = metadata.get("language", "")
            license_identifier = metadata.get("license", {}).get("license", "") if metadata.get("license") else ""
            title = metadata.get("titles", {})[0].get("title", "") if metadata.get("titles") else ""
            description = metadata.get("descriptions", {})[0].get("description", "") if metadata.get(
                "descriptions") else ""
            publication_state = metadata.get("publication_state", "")
            publication_date = metadata.get("publication_date", "")
            version = metadata.get("version", "")
            authors = []
            for creator in metadata.get("creators", {}):
                authors.append(creator["creator_name"].strip())
            for contributor in metadata.get("contributors", {}):
                authors.append(contributor["contributor_name"].strip())

            """
            It is possible to get different alternate identifiers for the resource. 
            Like isbn, doi, etc. This may be needed later
            
            a_id, a_id_type = "", ""
            alternate_identifiers = {}
            if "alternate_identifiers" in metadata:
                for id in metadata["alternate_identifiers"]:
                    a_id = id["alternate_identifier"]
                    a_id_type = id["alternate_identifier_type"]
                    alternate_identifiers[a_id_type] = a_id
            """
            resource_types = []
            for resource in metadata.get("resource_types", ""):
                resource_types.append(resource["resource_type_general"])
            category = resource_types[0] if len(resource_types) == 1 else "CreativeWork"

            if category == "Dataset":
                dataset = Dataset()
                dataset.source = 'Eudat'
                dataset.name = title
                dataset.description = description
                dataset.datePublished = publication_date
                dataset.url = url
                dataset.license = license_identifier
                dataset.inLanguage = language
                dataset.identifier = doi
                for item in authors:
                    person = Person()
                    person.type = 'Person'
                    person.source = 'Eudat'
                    person.name = item
                    dataset.author.append(person)
                dataset.version = version
                dataset.creativeWorkStatus = publication_state
                results['resources'].append(dataset)

            elif category in ["Text", "Report", "Preprint", "PeerReview", "JournalArticle", "Journal", "Dissertation",
                              "ConferenceProceeding", "BookChapter", "Book"]:
                article = Article()
                article.source = 'Eudat'
                article.name = title
                article.description = description
                article.datePublished = publication_date
                article.inLanguage = language
                article.url = url
                article.identifier = doi
                article.license = license_identifier
                for item in authors:
                    person = Author()
                    person.type = 'Person'
                    person.source = 'Eudat'
                    person.name = item
                    article.author.append(person)
                article.version = version
                article.creativeWorkStatus = publication_state
                results['publications'].append(article)

            else:
                work = CreativeWork()
                work.source = 'Eudat'
                work.name = title
                work.description = description
                work.datePublished = publication_date
                work.inLanguage = language
                work.url = url
                work.identifier = doi
                work.license = license_identifier
                for item in authors:
                    person = Person()
                    person.type = 'Person'
                    person.source = 'Eudat'
                    person.name = item
                    work.author.append(person)
                work.version = version
                work.creativeWorkStatus = publication_state
                work.genre = category
                results['others'].append(work)

    # logger.info(f"Got {len(results)} records from Eudat")
    return results