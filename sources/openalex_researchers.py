import requests
from objects import thing, Article, Author, Organization
from objects import thing, Article, Author, Organization
import logging
import utils
from sources import data_retriever
import traceback
from openai import OpenAI
import json
from openai import OpenAI
import json
# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

def generate_string_from_keys(dictionary):
    keys_list = list(dictionary.keys())
    keys_string = " ".join(keys_list)
    return keys_string

@utils.timeit
def search(search_term: str, results):

    source = "OPENALEX Researchers"

    try:
        search_result = data_retriever.retrieve_data(source=source,
                                                     base_url=utils.config["search_url_openalex_researchers"],
                                                     search_term=search_term,
                                                     results=results)
        total_records_found = search_result['meta']['count']
        hits = search_result.get("results", [])
        total_hits = len(hits)
        logger.info(f'{source} - {total_records_found} records matched; pulled top {total_hits}')

        if int(total_hits) > 0:
            for hit in hits:

                author = Author()
                # info = hit.get('info',{})
                author.orcid = hit.get("ids", {}).get("orcid", "")
                author.name = hit.get('display_name', '')
                alias = hit.get('display_name_alternatives', {})
                if isinstance(alias, str):
                    author.alternateName.append(alias)
                if isinstance(alias, list):
                    for _alias in alias:
                        author.alternateName.append(_alias)

                affiliations = hit.get('affiliations', {})
                if isinstance(affiliations, list):
                    for affiliation in affiliations:
                        institution =  affiliation.get('institution', {})
                        if isinstance(institution, dict):
                            _organization = Organization()
                            _organization.name = institution.get('display_name', '')
                            years = affiliation.get('years', [])
                            if(len(years) > 1): _organization.keywords.append(f'{years[-1]}-{years[0]}')
                            else: _organization.keywords.append(f'{years[0]}')
                            author.affiliation.append(_organization)

                # topics = hit.get('topics', {})
                # if isinstance(topics, list):
                #     for topic in topics:
                #         name =  topic.get('display_name', '')
                #         author.researchAreas.append(name)
                # topics = hit.get('topic_share', {})
                # if isinstance(topics, list):
                #     for topic in topics:
                #         name =  topic.get('display_name', '')
                #         author.researchAreas.append(name)
                topics = hit.get('x_concepts', {})
                if isinstance(topics, list):
                    for topic in topics:
                        name =  topic.get('display_name', '')
                        author.researchAreas.append(name)

                author.works_count = hit.get('works_count', '')
                author.cited_by_count = hit.get('cited_by_count', '')

                _source = thing()
                _source.name = 'OPENALEX'
                _source.identifier = hit.get("ids", {}).get("openalex", "").replace('https://openalex.org/','')
                author.source.append(_source)

                search_result_semantic = data_retriever.retrieve_data(source=source,
                                                    base_url="https://api.semanticscholar.org/graph/v1/author/search?fields=name,url,externalIds,paperCount,citationCount&query=",
                                                    search_term= author.name.replace(" ", "+"),
                                                    results={})
                semantic_hits = search_result_semantic.get("data", [])
                for semantic_hit in semantic_hits:
                    if semantic_hit.get("externalIds", {}).get("ORCID", "") == author.orcid.replace('https://orcid.org/', ''):
                        author.works_count = semantic_hit.get('paperCount', '')
                        author.cited_by_count = semantic_hit.get('citationCount', '')
                        semanticId = semantic_hit.get("authorId", "")
                        _source = thing()
                        _source.name = 'SEMANITCSCHOLAR'
                        _source.identifier = semanticId
                        _source.url = semantic_hit.get("url", "")
                        author.source.append(_source)
                        break

                results['researchers'].append(author)


    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())

def convert_to_string(value):
    if isinstance(value, list):
        return ", ".join(convert_to_string(item) for item in value if item not in ("", [], {}, None))
    elif hasattr(value, '__dict__'):  # Check if the value is an instance of a class
        details = vars(value)
        return ", ".join(f"{key}: {convert_to_string(val)}" for key, val in details.items() if val not in ("", [], {}, None))
    return str(value)


def get_researcher_details(url):

    source = "Researcher"
    url = json.loads(url)

    try:
        hit = data_retriever.retrieve_data(source=source,
                                            base_url="https://api.openalex.org/authors/",
                                            search_term=url[0]['sid'],
                                            results={})

        researcher = Author()
        researcher.url = json.dumps(url)
        researcher.orcid = hit.get("ids", {}).get("orcid", "")
        researcher.name = hit.get('display_name', '')
        alias = hit.get('display_name_alternatives', {})
        if isinstance(alias, str):
            researcher.alternateName.append(alias)
        if isinstance(alias, list):
            for _alias in alias:
                researcher.alternateName.append(_alias)

        affiliations = hit.get('affiliations', {})
        if isinstance(affiliations, list):
            for affiliation in affiliations:
                institution =  affiliation.get('institution', {})
                if isinstance(institution, dict):
                    _organization = Organization()
                    _organization.name = institution.get('display_name', '')
                    years = affiliation.get('years', [])
                    if(len(years) > 1): _organization.keywords.append(f'{years[-1]}-{years[0]}')
                    else: _organization.keywords.append(f'{years[0]}')
                    researcher.affiliation.append(_organization)

        topics = hit.get('topics', {})
        if isinstance(topics, list):
            for topic in topics:
                name =  topic.get('display_name', '')
                researcher.researchAreas.append(name)
        # topics = hit.get('topic_share', {})
        # if isinstance(topics, list):
        #     for topic in topics:
        #         name =  topic.get('display_name', '')
        #         researcher.researchAreas.append(name)
        # topics = hit.get('x_concepts', {})
        # if isinstance(topics, list):
        #     for topic in topics:
        #         name =  topic.get('display_name', '')
        #         researcher.researchAreas.append(name)

        _source = thing()
        _source.name = 'OPENALEX'
        _source.identifier = hit.get("ids", {}).get("openalex", "").replace('https://openalex.org/','')
        researcher.source.append(_source)


        ##### uncomment to search openalex for publications...
        # search_result = data_retriever.retrieve_data(source=source,
        #                                             base_url="https://api.openalex.org/works?filter=author.id:",
        #                                             search_term=researcher.source[0].identifier,
        #                                             results={})
        # total_records_found = search_result['meta']['count']
        # hits = search_result.get("results", [])
        # total_hits = len(hits)
        # logger.info(f'{source} - {total_records_found} records matched; pulled top {total_hits}')
        # if int(total_hits) > 0:
        #     for hit in hits:

        #             publication = Article()

        #             publication.name = utils.remove_html_tags(hit.get("title", ""))
        #             publication.url = hit.get("id", "") # not a valid url, openalex is currently working on their web interface.
        #             publication.identifier = hit.get("doi", "").replace("https://doi.org/", "")
        #             publication.datePublished = hit.get("publication_date", "")
        #             publication.inLanguage.append(hit.get("language", ""))
        #             publication.license = hit.get("primary_location", {}).get("license", "")
        #             # publication.publication = hit.get("primary_location", {}).get("source", {}).get("display_name", "")

        #             abstract_inverted_index = hit.get("abstract_inverted_index", {})
        #             publication.description = generate_string_from_keys(abstract_inverted_index) # Generate the string using keys from the dictionary
        #             publication.abstract = publication.description

        #             authorships = hit.get("authorships", [])
        #             for authorship in authorships:

        #                 authors = authorship.get("author", {})

        #                 _author = Author()
        #                 _author.type = 'Person'
        #                 _author.name = authors.get("display_name", "")
        #                 _author.identifier = authors.get("orcid", "")
        #                 publication.author.append(_author)

        #             # getattr(publication, "source").clear()
        #             _source = thing()
        #             _source.name = 'OPENALEX'
        #             _source.identifier = hit.get("id", "").replace("https://openalex.org/", "") # remove the base url and only keep the ID
        #             _source.url = hit.get("id", "") # not a valid url, openalex is currently working on thier web interface.
        #             publication.source.append(_source)

        #             researcher.works.append(publication)


        # search semantic scholar...
        search_result = data_retriever.retrieve_data(source=source,
                                                    base_url="https://api.semanticscholar.org/graph/v1/author/search?fields=name,url,externalIds,paperCount,citationCount&query=",
                                                    search_term= researcher.name.replace(" ", "+"),
                                                    results={})
        hits = search_result.get("data", [])
        for hit in hits:
            if hit.get("externalIds", {}).get("ORCID", "") == researcher.orcid.replace('https://orcid.org/', ''):
                researcher.works_count = hit.get('paperCount', '')
                researcher.cited_by_count = hit.get('citationCount', '')
                semanticId = hit.get("authorId", "")
                _source = thing()
                _source.name = 'SEMANITCSCHOLAR'
                _source.identifier = semanticId
                _source.url = hit.get("url", "")
                researcher.source.append(_source)
                break
        search_result = data_retriever.retrieve_data(source=source,
                                                    base_url=f'https://api.semanticscholar.org/graph/v1/author/{semanticId}/papers?fields=url,title,venue,year,authors,abstract',
                                                    search_term= "",
                                                    results={})

        hits = search_result.get("data", [])
        a = 0
        total_hits = len(hits)
        if int(total_hits) > 0:
            for hit in hits:

                    publication = Article()

                    publication.name = utils.remove_html_tags(hit.get("title", ""))
                    publication.url = hit.get("url", "")
                    publication.identifier = hit.get("title", "")
                    publication.description = hit.get("abstract", "")
                    # publication.identifier = hit.get("doi", "").replace("https://doi.org/", "")
                    publication.datePublished = hit.get("year", "")
                    # publication.inLanguage.append(hit.get("language", ""))
                    # publication.license = hit.get("primary_location", {}).get("license", "")
                    # publication.publication = hit.get("primary_location", {}).get("source", {}).get("display_name", "")

                    # abstract_inverted_index = hit.get("abstract_inverted_index", {})
                    # publication.description = generate_string_from_keys(abstract_inverted_index) # Generate the string using keys from the dictionary
                    # publication.abstract = publication.description
                    # abstract_inverted_index = hit.get("abstract_inverted_index", {})
                    # publication.description = generate_string_from_keys(abstract_inverted_index) # Generate the string using keys from the dictionary
                    # publication.abstract = publication.description

                    authorships = hit.get("authors", [])
                    for authorship in authorships:

                        # authors = authorship.get("author", {})
                        # authors = authorship.get("author", {})

                        _author = Author()
                        _author.type = 'Person'
                        _author.name = authorship.get("name", "")
                        # _author.identifier = authors.get("orcid", "")
                        publication.author.append(_author)

                    # getattr(publication, "source").clear()
                    _source = thing()
                    _source.name = 'SEMANTICSCHOLAR'
                    # _source.identifier = hit.get("id", "").replace("https://openalex.org/", "") # remove the base url and only keep the ID
                    # _source.url = hit.get("id", "") # not a valid url, openalex is currently working on thier web interface.
                    publication.source.append(_source)

                    researcher.works.append(publication)
                    a+=1

        ### uncomment to generate about section
        logger.info(f'Getting publications {a}')
        details = vars(researcher)
        # Convert the details into a string format
        details_str = "\n".join(f"{key}: {convert_to_string(value)}" for key, value in details.items() if (value not in ("", [], {}, None) and key not in ("works", "source","orcid")))
        prompt = f"Generate a 2-3 line 'About' section for a researcher based on the following details:\n{details_str}"
        client = OpenAI(
            api_key=utils.env_config["OPENAI_API_KEY"],
        )
        logger.info('sent message to openai')
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f'{prompt}',
                }
            ],
            model="gpt-3.5-turbo",
        )
        # about_section = response.choices[0].text.strip()
        researcher.about = chat_completion.choices[0].message.content.strip()

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())

    return researcher

def get_researcher_banner(researcher: Author):
    try:
        details = vars(researcher)
        details_str = "\n".join(f"{convert_to_string(value)}" for key, value in details.items() if (value not in ("", [], {}, None) and key in ("researchAreas")))
        prompt = f"A banner for researcher with following research areas:\n{researcher.about}"
        client = OpenAI(
                        api_key=utils.env_config["OPENAI_API_KEY"],
                )
        response = client.images.generate(
        model="dall-e-2",
        prompt=prompt,
        size="512x512",
        quality="standard",
        response_format="b64_json",
        n=1,
        )
        researcher.banner = response.data[0].b64_json

        researcher.works.append(publication)
        a+=1

        ### uncomment to generate about section
        logger.info(f'Getting publications {a}')
        details = vars(researcher)
        # Convert the details into a string format
        details_str = "\n".join(f"{key}: {convert_to_string(value)}" for key, value in details.items() if (value not in ("", [], {}, None) and key not in ("works", "source","orcid")))
        prompt = f"Generate a 2-3 line 'About' section for a researcher based on the following details:\n{details_str}"
        client = OpenAI(
            api_key=utils.env_config["OPENAI_API_KEY"],
        )
        logger.info('sent message to openai')
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f'{prompt}',
                }
            ],
            model="gpt-3.5-turbo",
        )
        # about_section = response.choices[0].text.strip()
        researcher.about = chat_completion.choices[0].message.content.strip()

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())

    return researcher

def get_researcher_banner(researcher: Author):
    try:
        details = vars(researcher)
        details_str = "\n".join(f"{convert_to_string(value)}" for key, value in details.items() if (value not in ("", [], {}, None) and key in ("researchAreas")))
        prompt = f"A banner for researcher with following research areas:\n{researcher.about}"
        client = OpenAI(
                        api_key=utils.env_config["OPENAI_API_KEY"],
                )
        response = client.images.generate(
        model="dall-e-2",
        prompt=prompt,
        size="512x512",
        quality="standard",
        response_format="b64_json",
        n=1,
        )
        researcher.banner = response.data[0].b64_json

    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())

    return researcher

    return researcher