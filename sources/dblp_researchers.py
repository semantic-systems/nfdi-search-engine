import requests
from objects import thing, Article, Author, Organization
import logging
import utils
from sources import data_retriever
import utils
from main import app

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)        

    hits = search_result['result']['hits']
    total_records_found = hits['@total']
    total_hits = hits['@sent']

    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")

    if int(total_hits) > 0:
        hits = hits['hit']         
        for hit in hits:
                
            author = Author()
            info = hit.get('info',{})

            author.name = info.get('author', '')
            alias = info.get('aliases', {}).get('alias', '')
            if isinstance(alias, str):
                author.alternateName.append(alias)
            if isinstance(alias, list):
                for _alias in alias:
                    author.alternateName.append(_alias)

            affiliations = info.get('notes', {}).get('note', {})
            if isinstance(affiliations, list):
                for affiliation in affiliations:
                    if affiliation.get('@type', '') == 'affiliation':
                        _organization = Organization()
                        _organization.name = affiliation.get('text', '')
                        author.affiliation.append(_organization)
            if isinstance(affiliations, dict):
                if affiliations.get('@type', '') == 'affiliation':
                    _organization = Organization()
                    _organization.name = affiliations.get('text', '')
                    author.affiliation.append(_organization)
                                        
            # author.works_count = ''
            # author.cited_by_count = ''

            _source = thing()
            _source.name = 'DBLP'
            _source.identifier = hit.get("@id", "")
            _source.url = info.get("url", "")                         
            author.source.append(_source)

            results['researchers'].append(author)     