from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app
import requests

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 

    details_api = "https://orkg.org/api/"
    author_url = "https://orkg.org/author/"

    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources) 

    total_hits = search_result['totalElements']
    total_records_pulled = search_result['numberOfElements']
    utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {total_records_pulled}")

    hits = search_result['content']
    for hit in hits:
        id = hit.get('id', None)
        classes = hit.get('classes', [])
        if 'Paper' in classes:
            api_url = details_api + 'papers/' + id
            response = requests.get(api_url)
            paper = response.json()
            publication = Article()
            _source = thing()
            _source.name = source
            publication.source.append(_source)
            publication.name = paper.get('title', '')
            publication.url = api_url
            publication.identifier = paper.get('identifiers', {}).get('doi', '')
            month = paper.get('publication_info', {}).get('published_month', None)
            year = paper.get('publication_info', {}).get('published_year', None)
            if month is not None and year is not None:
                publication.datePublished = str(month) + '/' + str(year)
            elif year is not None:
                publication.datePublished = str(year)

            if paper.get('authors', []):
                for item in paper.get('authors', []):
                    author = Author()
                    author.type = 'Person'
                    author.name = item.get('name', '')
                    author.identifier = item.get('identifiers', {}).get('orcid', '')
                    if item.get('id', ''):
                        author.url = author_url + item.get('id')
                    publication.author.append(author)
            
            _source = thing()
            _source.name = 'ORKG'
            _source.identifier = id
            _source.url = api_url                        
            publication.source.append(_source)
            
            results['publications'].append(publication)

    
