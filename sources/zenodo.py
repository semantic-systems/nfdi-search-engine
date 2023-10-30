import requests
import utils
# from objects import Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Person, LearningResource, CreativeWork, VideoObject, ImageObject
from objects import thing, Article, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
import logging
from sources import data_retriever

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term, results):

    source = "Zenodo"
    try:
        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=utils.config["search_url_zenodo"],
                                                     search_term=search_term,
                                                     results=results)      

        hits = search_result['hits']
        total_hits = hits['total']

        logger.info(f'{source} - {total_hits} hits found')  

        if int(total_hits) > 0:
            hits = hits['hits']         
    
            for hit in hits:
                
                metadata = hit.get('metadata', {})
                resource_type = metadata.get('resource_type', {}).get('type')

                if resource_type.upper() == 'PUBLICATION':
                    digitalObj = Article() 
                elif resource_type.upper() in ['PRESENTATION', 'POSTER']:
                    digitalObj = CreativeWork() 
                elif resource_type.upper() == 'DATASET':
                    digitalObj = Dataset() 
                elif resource_type.upper() == 'VIDEO':
                    digitalObj = VideoObject() 
                elif resource_type.upper() == 'IMAGE':
                    digitalObj = ImageObject() 
                elif resource_type.upper() == 'LESSON':
                    digitalObj = LearningResource() 
                elif resource_type.upper() == 'OTHER':
                    digitalObj = CreativeWork() 
                else:
                    print('This resource type is still not defined:', resource_type.upper())
                    digitalObj = CreativeWork()
                    
                digitalObj.identifier = hit.get('doi', '')
                digitalObj.name = hit.get('title', '')
                digitalObj.url = hit.get('links', {}).get('self', '')  
                
                digitalObj.description = utils.remove_html_tags(metadata.get('description', ''))
                
                keywords = metadata.get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        digitalObj.keywords.append(keyword)               
                
                language = metadata.get('language', '')
                digitalObj.inLanguage.append(language)

                digitalObj.datePublished = metadata.get('publication_date', '')
                digitalObj.license = metadata.get('license', {}).get('id', '')

                authors = metadata.get("creators", [])                        
                for author in authors:
                    _author = Author()
                    _author.type = 'Person'
                    _author.name = author.get("name", "")
                    _author.identifier = author.get("orcid", "")
                    _author.affiliation = author.get("affiliation", "")
                    digitalObj.author.append(_author)  

                _source = thing()
                _source.name = source
                _source.identifier = hit.get("id", "")
                _source.url = hit.get('links', {}).get('self_html', '')                      
                digitalObj.source.append(_source)                

                if resource_type.upper() == 'PUBLICATION':
                    digitalObj.abstract = digitalObj.description
                    results['publications'].append(digitalObj)
                elif resource_type.upper() in ['PRESENTATION', 'POSTER', 'DATASET', 'SOFTWARE', 'VIDEO', 'IMAGE', 'LESSON']:                
                    results['resources'].append(digitalObj)                
                else:
                    results['others'].append(digitalObj)   

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)
    
    except Exception as ex:
        logger.error(f'Exception: {str(ex)}')