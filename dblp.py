import utils
import requests
from objects import Person, Article
import json


def search(name, g, results):
    """
        Request from the dblp database and gathers it in the data types
    Args:
        name: keyword to search for
        g: graph containing the search answer
        results: search answer formatted into the data types of Person and Article

    Returns:
        the graph object and the results array
    """
    headers = {'Accept': 'application/json'}

    response = requests.get('https://dblp.uni-trier.de/search?q=' + name, headers=headers)
    print(response.status_code)
    # TODO unclear why here are only a few but now all results returned
    metadata = utils.extract_metadata(response.content)

    # TODO unclear why this loop takes so long
    for data in metadata['microdata']:
        if data['@type'] == 'Person':
            possible_author = utils.is_author_in(data["name"], results)
            if possible_author:
                results[results.index(possible_author)] = Person(data["name"], possible_author.URL + ' - ' +
                                                                 data["url"])
            else:
                results.append(Person(data["name"], data["url"]))
            g.parse(data=json.dumps(data), format='json-ld')
        if data['@type'] == 'ScholarlyArticle':
            author = ""
            if type(data["author"]) == list:
                author = ','.join([authors["name"] for authors in data["author"]])
            else:
                author = data["author"]

            url = ""
            if type(data["url"]) == list:
                url = ' - '.join(data["url"])
            else:
                url = data["url"]

            possible_article = utils.is_article_in(data["name"], results)
            if possible_article:
                print(possible_article.title)
                results[results.index(possible_article)] = Article(possible_article.title,
                                                                   possible_article.URL + ' - ' + url,
                                                                   author, possible_article.date)
            else:
                results.append(Article(data["name"], url, author, data["datePublished"]))
            g.parse(data=json.dumps(data), format='json-ld')

    print(f"Graph g has {len(g)} statements.")

    response.close()
    return g, results