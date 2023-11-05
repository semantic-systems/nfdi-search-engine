import requests
import utils
# from objects import Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Person, LearningResource, CreativeWork, VideoObject, ImageObject
from objects import thing, Article, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
import logging
from sources import data_retriever
import traceback

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')

@utils.timeit
def search(search_term, results):

    source = "Openaire Products"
    try:
        search_result = data_retriever.retrieve_data(source=source, 
                                                     base_url=utils.config["search_url_openaire_products"],
                                                     search_term=search_term,
                                                     results=results)      

        response = search_result.get("response", {})
        total_records_found = response.get("header", {}).get("total", "").get("$", "")
        hits = response.get("results", {}).get("result",[])
        total_hits = len(hits)

        logger.info(f'{source} - {total_hits} hits pulled; total records found: {total_records_found}')  

        if int(total_hits) > 0:     
    
            for hit in hits:
                
                metadata = hit.get('metadata', {}).get("oaf:entity", {})
                resource_type = metadata.get('oaf:result', {}).get('resulttype', {}).get("@classname", "OTHER").upper()

                print("Resource Type:", resource_type)

                if resource_type == 'PUBLICATION':
                    digitalObj = Article() 
                elif resource_type == 'SOFTWARE':
                    digitalObj = SoftwareApplication() 
                elif resource_type == 'DATASET':
                    digitalObj = Dataset() 
                # elif resource_type in ['PRESENTATION', 'POSTER']:
                #     digitalObj = CreativeWork()                 
                # elif resource_type == 'VIDEO':
                #     digitalObj = VideoObject() 
                # elif resource_type == 'IMAGE':
                #     digitalObj = ImageObject() 
                # elif resource_type == 'LESSON':
                #     digitalObj = LearningResource()                 
                elif resource_type.upper() == 'OTHER':
                    digitalObj = CreativeWork() 
                else:
                    print('This resource type is still not defined:', resource_type)
                    digitalObj = CreativeWork()

                oaf_result = metadata.get("oaf:result", {})

                # originalId is another tag which contains pid information
                pids = oaf_result.get("pid", [])
                if isinstance(pids, dict):
                    digitalObj.identifier = pids.get('$', '')
                if isinstance(pids, list):
                    for pid in pids:
                        if pid.get("@classid").upper() == "DOI":
                            digitalObj.identifier = pid.get('$', '')
                
                original_sources = oaf_result.get("collectedfrom", [])
                if isinstance(original_sources, dict):
                    digitalObj.originalSource = original_sources.get("@name", "")
                if isinstance(original_sources, list):
                    digitalObj.originalSource = next(iter(original_sources)).get("@name", "")
                
                titles = oaf_result.get("title", [])
                if isinstance(titles, dict):
                    digitalObj.name = utils.remove_html_tags(titles.get("$", ""))
                if isinstance(titles, list):
                    for title in titles:
                        if title.get("@classid","").upper() == "MAIN TITLE":
                            digitalObj.name = utils.remove_html_tags(title.get("$", ""))

                descriptions = oaf_result.get("description", [])
                if isinstance(descriptions, dict):
                    digitalObj.description = utils.remove_html_tags(descriptions.get("$", ""))
                if isinstance(descriptions, list):
                    for description in descriptions:
                        digitalObj.description += utils.remove_html_tags(description.get("$", "")) + "<br/>"

                children_instance = oaf_result.get('children', {}).get('instance', {})
                if isinstance(children_instance, dict):
                    digitalObj.url = children_instance.get('webresource', {}).get('url', {}).get('$', '')
                if isinstance(children_instance, list):
                    digitalObj.url = next(iter(children_instance)).get('webresource', {}).get('url', {}).get('$', '')
                                       
                keywords = oaf_result.get('subject', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        digitalObj.keywords.append(keyword.get("$", ""))               
                
                language = oaf_result.get('language', {}).get("@classid", "")
                digitalObj.inLanguage.append(language)

                digitalObj.datePublished = oaf_result.get('dateofacceptance', {}).get("$", "")
                digitalObj.license = oaf_result.get('bestaccessright', {}).get('@classid', '')

                authors = oaf_result.get("creator", [])  
                if isinstance(authors, dict): 
                    _author = Author()
                    _author.type = 'Person'
                    _author.name = authors.get("$", "")
                    _author.identifier = authors.get("@orcid_pending", "")
                    digitalObj.author.append(_author) 
                if isinstance(authors, list): 
                    for author in authors:
                        _author = Author()
                        _author.type = 'Person'
                        _author.name = author.get("$", "")
                        _author.identifier = author.get("@orcid_pending", "")
                        digitalObj.author.append(_author)  

                _source = thing()
                _source.name = source
                _source.identifier = hit.get("header", {}).get("dri:objIdentifier", {}).get("$", "")
                _source.url = digitalObj.url                   
                digitalObj.source.append(_source)                

                if resource_type == 'PUBLICATION':
                    digitalObj.abstract = digitalObj.description
                    results['publications'].append(digitalObj)
                elif resource_type in ['DATASET', 'SOFTWARE']:                
                    results['resources'].append(digitalObj)                
                else:
                    results['others'].append(digitalObj)   

    except requests.exceptions.Timeout as ex:
        logger.error(f'Timed out Exception: {str(ex)}')
        results['timedout_sources'].append(source)
    
    except Exception as ex:        
        logger.error(f'Exception: {str(ex)}')
        logger.error(traceback.format_exc())