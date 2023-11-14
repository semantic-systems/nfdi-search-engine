import requests
from objects import thing, Dataset, Author, Article, CreativeWork, VideoObject
import logging
import utils
from sources import data_retriever
from datetime import datetime
from dateutil import parser
import traceback

logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term: str, results):

    source = "EUDAT"

    source_url_direct_access = "https://b2share.eudat.eu/records/"

    try:

        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=utils.config["search_url_eudat"],
                                                     search_term=search_term,
                                                     results=results)
    
        hits = search_result['hits']
        total_hits = hits['total']

        logger.info(f'{source} - {total_hits} records matched; pulled top {total_hits}')          

        if int(total_hits) > 0:
            hits = hits.get("hits", [])         

            for hit in hits:

                metadata = hit.get('metadata', {})    
                resource_type = 'OTHER' # resource type is defaulted to 'Other'   
                resource_types = metadata.get('resource_types', [])
                if len(resource_types) > 0:
                    resource_type = resource_types[0].get('resource_type_general', '').upper()

                print('Resource Type:', resource_type.upper())
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
                _source.url = source_url_direct_access + _source.identifier                    
                digitalObj.source.append(_source)  

                if resource_type in ['DATASET', 'MODEL', 'AUDIOVISUAL']:
                    results['resources'].append(digitalObj)    
                elif resource_type.upper() in ['TEXT']:
                    digitalObj.abstract = digitalObj.description
                    results['publications'].append(digitalObj)                
                else:
                    results['others'].append(digitalObj)   
                
                # resource_types = []
                # for resource in metadata.get("resource_types", ""):
                #     resource_types.append(resource["resource_type_general"])
                # category = resource_types[0] if len(resource_types) == 1 else "CreativeWork"

                # elif category in ["Text", "Report", "Preprint", "PeerReview", "JournalArticle", "Journal", "Dissertation",
                #                 "ConferenceProceeding", "BookChapter", "Book"]:        
        
    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)
        
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())