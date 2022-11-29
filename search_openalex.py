from diophila import OpenAlex
import json


def find(search_key):
    oa = OpenAlex()
    search_result = {
        "@context": "http://schema.org/"
    }
    works_search_result = find_works(oa, search_key)
    authors_search_result = find_authors(oa, search_key)
    api_response_concepts = oa.get_list_of_concepts(search=search_key)
    search_result.update({"@graph": [{"graph1": works_search_result}, {"graph2": authors_search_result}]})
    return search_result


def find_authors(oa, search_key):
    api_response_authors = oa.get_list_of_authors(search=search_key)
    list_of_authors = []
    for authors in api_response_authors:
        for author in authors['results']:
            if 'id' in author:
                concepts = []
                for concept in author['x_concepts']:
                    concepts.append(
                        {'@id': concept['id'], 'sameAs': concept['wikidata'], 'name': concept['display_name']})

                list_of_authors.append({
                    '@id': author['id'], '@type': 'Person', 'name': author['display_name'], 'ids': author['ids'],
                    'works_count': author['works_count'],
                    'cited_by_count': author['cited_by_count'],
                    'last_known_institution': author['last_known_institution'],
                    'x_concepts': concepts,
                    'works_api_url': author['works_api_url']
                })
        return list_of_authors


def find_works(oa, search_key):
    api_response_works = oa.get_list_of_works(search=search_key)

    list_of_works = []
    for works in api_response_works:
        for work in works['results']:
            if 'id' in work:
                list_of_works.append(parse_to_jsonld(work))

    return list_of_works


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


def parse_to_jsonld(work: object) -> dict:
    host_venue = work['host_venue']
    display_name = work['display_name']
    host_information = [{'@id': host_venue['id'], '@type': host_venue['type'],
                         'name': host_venue['display_name'], 'publisher': host_venue['publisher']
                         }]
    author_information = get_authorship_information(work['authorships'])
    concepts = []
    for concept in work['concepts']:
        concepts.append({'@id': concept['id'], 'sameAs': concept['wikidata'], 'name': concept['display_name']})

    temp = {
        '@id': work['id'], '@type': 'article', 'title': work['title'], 'doi': work['doi'],
        'publication_date': work['publication_date'],
        'host_venue': host_information, 'authors': author_information,
        'concepts': concepts,
        'cited_by_api_url': work['cited_by_api_url'],
        'referenced_works': work['referenced_works'],
        'related_works': work['related_works']
    }
    return temp
