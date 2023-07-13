import requests
#from objects import CreativeWork, Collection, Sound, Image, Dataset, Video, Event, Software, Service, Text
from objects import Dataset
import logging
from utils import guess_date


logger = logging.getLogger('nfdi_search_engine')


def search(search_string: str, results):
    """ Obtain the results from Eudat request and handles them accordingly.

          Args:
              search_string: keyword(s) to search for
              results: search answer formatted into different data types according to Eudat resource_types.

          Returns:
                the results array
          """
    api_url = 'https://b2share.eudat.eu/api/records/'
    result_url_start = 'https://b2share.eudat.eu/records/'
    response = requests.get(api_url, params={'q': search_string, 'sort': 'mostrecent'})
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
            # doi = metadata.get("DOI", "")
            # epic_pid = metadata.get("ePIC_PID", "")
            license_identifier = metadata.get("license", {}).get("license_identifier", "unknown")
            title = metadata.get("titles", {})[0].get("title", "")
            description = metadata.get("descriptions", {})[0].get("description", "")
            description = description[0:150] + "..." if description != "" else ""
            publication_state = metadata.get("publication_state", "")
            publication_date = metadata.get("publication_date", "")
            formatted_date = guess_date(publication_date)
            if publication_date != "":
                publication_date = formatted_date if formatted_date !="" else publication_date

            version = metadata.get("version", "")
            authors = []
            for creator in metadata.get("creators", {}):
                authors.append(creator["creator_name"].rstrip())

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
            for resource in metadata.get("resource_types", {}):
                resource_types.append(resource["resource_type_general"])

            category = resource_types[0] if len(resource_types) == 1 else "CreativeWork"

            # for now all categories got to "Dataset".
            results.append(Dataset(
                title=title,
                description=description,
                url=url,
                authors=", ".join(authors),
                date=publication_date))

            # Category matching for later use.
            """
            match category:
                case "Collection" | "Sound" | "Text":
                    results.append(category(
                        title=title,
                        description=description,
                        license_identifier=license_identifier,
                        publication_state=publication_state,
                        publication_date=publication_date,
                        authors=", ".join(authors),
                        url=url
                    ))

                case "Image" | "Video":
                    results.append(category(
                        title=title,
                        date=publication_date,
                        authors=", ".join(authors),
                        url=url
                    ))

                case "Event":
                    results.append(category(
                        title=title,
                        description=description,
                        start_date=publication_date,
                        # end_date="" ,
                        # authors=", ".join(authors),
                        url=url
                    ))

                case "Service":
                    results.append(category(
                        title=title,
                        description=description,
                        #date=publication_date,
                        provider=", ".join(authors),
                        url=url
                    ))

                case "Software":
                    results.append(category(
                        title=title,
                        description=description,
                        date=publication_date,
                        authors=", ".join(authors),
                        url=url,
                        version=version
                    ))

                case "Dataset":
                    results.append(category(
                        title=title,
                        description=description,
                        date=publication_date,
                        authors=", ".join(authors),
                        url=url
                    ))
                case other:
                    results.append(CreativeWork(
                        title=title,
                        description=description,
                        license_identifier=license_identifier,
                        publication_state=publication_state,
                        publication_date=publication_date,
                        authors=", ".join(authors),
                        url=url
                    ))
                    
                    """

    logger.info(f"Got {len(results)} records from Eudat")

    return results




