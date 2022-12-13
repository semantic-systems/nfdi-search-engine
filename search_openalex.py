from diophila import OpenAlex
import json
from objects import Person, Article
import utils


def open_alex(name, g, results):
    """
    Obtain the results from the database request handles them accordingly
        Initially authored by Tilahun Taffa
    Args:
        name: keyword to search for
        g: graph containing the search answer
        results: search answer formatted into the data types of Person and Article

    Returns:
        the graph object and the results array

    """
    serializable_results, results = find(name, results)
    search_result = json.dumps(serializable_results)
    g.parse(data=search_result, format='json-ld')
    return g, results


def find(search_key, results):
    oa = OpenAlex()
    search_result = {
        "@context": "http://schema.org/"
    }
    works_search_result, results = find_works(oa, search_key, results)
    authors_search_result, results = find_authors(oa, search_key, results)
    api_response_concepts = oa.get_list_of_concepts(search=search_key)
    search_result.update({"@graph": [{"graph1": works_search_result}, {"graph2": authors_search_result}]})
    return search_result, results


def find_authors(oa, search_key, results):
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
                if author['display_name'] is None or author['id'] is None:
                    continue
                if not utils.is_author_in(author['display_name'], results):
                    results.append(Person(author['display_name'], author['id']))

        return list_of_authors, results


def find_works(oa, search_key, results):
    api_response_works = oa.get_list_of_works(search=search_key)

    list_of_works = []
    for works in api_response_works:
        for work in works['results']:
            if 'id' in work:
                list_of_works.append(parse_to_jsonld(work))

                if work["display_name"] is None or work["id"] is None or work["publication_year"] is None:
                    continue
                if len(work["authorships"]) == 1:
                    author = work["authorships"][0]["author"]["display_name"]
                else:
                    author = ','.join(
                        current_author["author"]["display_name"] for current_author in work["authorships"])
                if not utils.is_article_in(work["display_name"], results):
                    results.append(Article(work["display_name"], work["id"], author, str(work["publication_year"])))

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
