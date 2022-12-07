import requests

def search_sources(keyword):
    response = requests.get('http://127.0.0.1:5000/search?keyword=' + keyword)
    response.close()
    return response.json()["rich_snippet"]