from objects import thing, Dataset, Author, Article, CreativeWork, VideoObject
from typing import Iterable, Dict, Any, List
from sources import data_retriever
import utils
from main import app
from datetime import datetime
from dateutil import parser

from sources.base import BaseSource

class EUDAT(BaseSource):

    SOURCE = 'EUDAT'

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(source=self.SOURCE, 
                                                    base_url=app.config['DATA_SOURCES'][self.SOURCE].get('endpoint', ''),
                                                    search_term=search_term,
                                                    failed_sources=failed_sources)  

        return search_result
    
    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """

        hits = raw['hits']
        total_hits = hits['total']
        utils.log_event(type="info", message=f"{self.SOURCE} - {total_hits} records matched; pulled top {total_hits}")              

        if int(total_hits) > 0:
            hits = hits.get("hits", [])
            return hits
        return None
        
    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        metadata = hit.get('metadata', {})    
        resource_type = 'OTHER' # resource type is defaulted to 'Other'   
        resource_types = metadata.get('resource_types', [])
        if len(resource_types) > 0:
            resource_type = resource_types[0].get('resource_type_general', '').upper()

        # print('Resource Type:', resource_type.upper())
        if resource_type == 'DATASET':
            digitalObj = Dataset() 
        elif resource_type in ['TEXT']:
            digitalObj = Article()
        elif resource_type in ['MODEL']:
            digitalObj = CreativeWork()
        elif resource_type in ['AUDIOVISUAL']:
            digitalObj = VideoObject()                 
        elif resource_type == 'OTHER':
            digitalObj = CreativeWork() 
        else:
            print(f'{self.SOURCE} - This resource type is still not defined:', resource_type.upper())
            digitalObj = CreativeWork()
            
        digitalObj.additionalType = resource_type
        digitalObj.identifier = metadata.get('DOI', '').replace("https://doi.org/","")
        digitalObj.name = next(iter(metadata.get('titles', [])), {}).get("title", "")
        digitalObj.url = hit.get('links', {}).get('self', '')  # this gives the json response
        
        
        digitalObj.description = utils.remove_html_tags(next(iter(metadata.get('descriptions', [])), {}).get("description", ""))
        
        
        keywords = metadata.get('keywords', [])
        for keyword in keywords:
            digitalObj.keywords.extend(keyword.get("keyword", "").split(","))  #keyword field contains comma seperated keywords  

        language = next(iter(metadata.get('languages', [])), {}).get("language_identifier", "")
        digitalObj.inLanguage.append(language)

        digitalObj.datePublished = datetime.strftime(parser.parse(hit.get('created', "")), '%Y-%m-%d')
        digitalObj.license = metadata.get('license', {}).get('license', '')

        authors = metadata.get("creators", [])                        
        for author in authors:
            _author = Author()
            _author.additionalType = 'Person'
            _author.name = author.get("creator_name", "")

            author_source = thing(
                name=self.SOURCE
            )

            _author.source.append(author_source)

            if ";" in _author.name:
                authors_names = _author.name.split(";")
                for author_name in authors_names:
                    __author = Author()
                    __author.additionalType = 'Person'
                    __author.name = author_name
                digitalObj.author.append(__author)  
            else:
                digitalObj.author.append(_author)  

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("id", "")
        # _source.url = hit.get('links', {}).get('self', '')  # this gives json response
        _source.url = app.config['DATA_SOURCES'][self.SOURCE].get('record-base-url', '') + _source.identifier                    
        digitalObj.source.append(_source)  

        return digitalObj
    
    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)

        if raw == None:
            return

        hits = self.extract_hits(raw)

        if hits:
            for hit in hits:
                digitalObj = self.map_hit(hit)
                resource_type = digitalObj.additionalType

                if resource_type in ['DATASET', 'MODEL']:
                    results['resources'].append(digitalObj)    
                elif resource_type.upper() in ['TEXT']:
                    digitalObj.abstract = digitalObj.description
                    results['publications'].append(digitalObj)                
                else: # 'AUDIOVISUAL'
                    results['others'].append(digitalObj)   

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    """
    Entrypoint to search EUDAT objects.
    """
    EUDAT().search(source, search_term, results, failed_sources)