import requests


def search_sources(keyword):
    """
    Creates request for the API sending the keyword to look for.

    Args:
        keyword: word to search in the databases

    Returns:
        JSON response with the rich snippet.
        TODO integrate the graph in the response once it is managed in the GUI
    """
    response = requests.get('http://127.0.0.1:5000/search?keyword=' + keyword)
    response.close()
    return response.json()["rich_snippet"]