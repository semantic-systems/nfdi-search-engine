from objects import thing, Dataset, Author, Article, CreativeWork, VideoObject
from sources import data_retriever
import utils
from main import app
from datetime import datetime
from dateutil import parser


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)     
    
    hits = search_result['hits']
    total_hits = hits['total']
    utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {total_hits}")              

    if int(total_hits) > 0:
        hits = hits.get("hits", [])         

        for hit in hits:

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
                print('This resource type is still not defined:', resource_type.upper())
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
                _author.type = 'Person'
                _author.name = author.get("creator_name", "")

                if ";" in _author.name:
                    authors_names = _author.name.split(";")
                    for author_name in authors_names:
                        __author = Author()
                        __author.type = 'Person'
                        __author.name = author_name
                    digitalObj.author.append(__author)  
                else:
                    digitalObj.author.append(_author)  

            _source = thing()
            _source.name = source
            _source.identifier = hit.get("id", "")
            # _source.url = hit.get('links', {}).get('self', '')  # this gives json response
            _source.url = app.config['DATA_SOURCES'][source].get('record-base-url', '') + _source.identifier                    
            digitalObj.source.append(_source)  

            if resource_type in ['DATASET', 'MODEL']:
                results['resources'].append(digitalObj)    
            elif resource_type.upper() in ['TEXT']:
                digitalObj.abstract = digitalObj.description
                results['publications'].append(digitalObj)                
            else: # 'AUDIOVISUAL'
                results['others'].append(digitalObj)   
            
            # resource_types = []
            # for resource in metadata.get("resource_types", ""):
            #     resource_types.append(resource["resource_type_general"])
            # category = resource_types[0] if len(resource_types) == 1 else "CreativeWork"

            # elif category in ["Text", "Report", "Preprint", "PeerReview", "JournalArticle", "Journal", "Dissertation",
            #                 "ConferenceProceeding", "BookChapter", "Book"]:        
    
