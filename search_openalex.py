import logging
from typing import List

from diophila import OpenAlex

from objects import Person, Article

logger = logging.getLogger('nfdi_search_engine')


def find(search_key: str, results: List):
    oa = OpenAlex()
    search_results_json_ld = {
        "@context": "http://schema.org/"
    }
    works_search_result, results = find_works(oa, search_key, results)
    authors_search_result, results = find_authors(oa, search_key, results)
    api_response_concepts = oa.get_list_of_concepts(search=search_key)
    search_results_json_ld.update(
        {
            "@graph":
                [
                    {"graph1": works_search_result},
                    {"graph2": authors_search_result}
                ]
        }
    )

    return search_results_json_ld


def find_authors(oa, search_key, results):
    api_response_authors = oa.get_list_of_authors(search=search_key)
    list_of_authors = []
    for authors in api_response_authors:
        for author in authors['results']:
            # E.g.:
            #  {
            #    "id": "https://openalex.org/A4222267058",
            #    "orcid": None,
            #    "display_name": "Ricardo Usbeck",
            #    "display_name_alternatives": [],
            #    "relevance_score": 184.41525,
            #    "works_count": 1,
            #    "cited_by_count": 4,
            #    "ids": {
            #      "openalex": "https://openalex.org/A4222267058"
            #    },
            #    "x_concepts": [
            #      ...
            #    ],
            #    "counts_by_year": [
            #      {
            #        "year": 2022,
            #        "works_count": 1,
            #        "cited_by_count": 4
            #      }
            #    ],
            #    "works_api_url": "https://api.openalex.org/works?filter=author.id:A4222267058",
            #    "updated_date": "2023-01-18T18:01:48.538514",
            #    "created_date": "2022-04-05"
            # }
            if 'id' in author:
                concepts = []
                for concept in author['x_concepts']:
                    # E.g.:
                    # {
                    #   "id": "https://openalex.org/C23123220",
                    #   "wikidata": "https://www.wikidata.org/wiki/Q816826",
                    #   "display_name": "Information retrieval",
                    #   "level": 1,
                    #   "score": 100
                    # }
                    concepts.append(
                        {
                            '@id': concept['id'],
                            'sameAs': concept['wikidata'],
                            'name': concept['display_name']
                        }
                    )

                list_of_authors.append({
                    '@id': author['id'],
                    '@type': 'Person',
                    'name': author['display_name'],
                    'ids': author['ids'],
                    'works_count': author['works_count'],
                    'cited_by_count': author['cited_by_count'],
                    'last_known_institution': author['last_known_institution'],
                    'x_concepts': concepts,
                    'works_api_url': author['works_api_url']
                })
                if author['display_name'] and author['id']:
                    results.append(
                        Person(
                            name=author['display_name'],
                            url=author['id']
                        )
                    )

        logger.info(f'Got {len(list_of_authors)} author records from OpenAlex')
        return list_of_authors, results


def find_works(oa, search_key, results):
    api_response_works = oa.get_list_of_works(search=search_key)

    list_of_works = []
    for works in api_response_works:
        for work in works['results']:
            if 'id' in work:
                list_of_works.append(parse_to_jsonld(work))

                if work["display_name"] is None \
                        or work["id"] is None \
                        or work["publication_year"] is None:
                    continue

                if len(work["authorships"]) == 1:
                    author = work["authorships"][0]["author"]["display_name"]
                else:
                    author = ', '.join(current_author["author"]["display_name"] for current_author in work["authorships"])

                results.append(
                    Article(
                        title=work["display_name"],
                        url=work["id"],
                        authors=author,
                        date=str(work["publication_year"])
                    )
                )

    logger.info(f'Got {len(list_of_works)} publication records from OpenAlex')
    return list_of_works, results


def update_list_of_works(param, list_of_works):
    if param not in list_of_works:
        list_of_works.append(param)
        return list_of_works


def get_authorship_information(work_authors):
    authors_info = []
    for work_author in work_authors:
        author = work_author['author']
        institutions = work_author['institutions']

        author_institution = []
        for institute in institutions:
            author_institution.append(
                {'@id': institute['id'], '@type': 'Organization', 'name': institute['display_name'],
                 'ror': institute['ror'], 'country_code': institute['country_code']})
        authors_info.append(
            {'@id': author['id'], '@type': 'Person', 'name': author['display_name'], 'orcid': author['orcid'],
             'author_position': work_author['author_position'],
             'affiliation': author_institution})
    return authors_info


def parse_to_jsonld(work: dict) -> dict:
    host_venue = work['host_venue']
    display_name = work['display_name']
    host_information = [{'@id': host_venue['id'], '@type': host_venue['type'],
                         'name': host_venue['display_name'], 'publisher': host_venue['publisher']
                         }]
    author_information = get_authorship_information(work['authorships'])
    concepts = []
    for concept in work['concepts']:
        concepts.append({'@id': concept['id'], 'sameAs': concept['wikidata'], 'name': concept['display_name']})

    return {
        '@id': work['id'], '@type': 'article', 'title': work['title'], 'doi': work['doi'],
        'publication_date': work['publication_date'],
        'host_venue': host_information, 'authors': author_information,
        'concepts': concepts,
        'cited_by_api_url': work['cited_by_api_url'],
        'referenced_works': work['referenced_works'],
        'related_works': work['related_works']
    }
