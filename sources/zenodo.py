from objects import thing, Article, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
from sources import data_retriever
import utils
from main import app
from typing import Union

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):  
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)     

    total_records_found = search_result.get("hits", {}).get("total", 0)
    hits = search_result.get("hits", {}).get("hits", [])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")

    if int(total_hits) > 0:
        for hit in hits:

            metadata = hit.get('metadata', {})
            resource_type = metadata.get('resource_type', {}).get('type','OTHER').upper()

            digitalObj = map_digital_obj(source, hit)

            if resource_type.upper() == 'PUBLICATION':
                results['publications'].append(digitalObj)
            elif resource_type.upper() in ['DATASET', 'SOFTWARE']:                
                results['resources'].append(digitalObj)                
            else: # 'PRESENTATION', 'POSTER', 'VIDEO', 'IMAGE', 'LESSON', OTHERS
                results['others'].append(digitalObj) 

# @utils.handle_exceptions
def map_digital_obj(source: str, hit: dict) -> Union[Article, CreativeWork, Dataset, VideoObject, ImageObject, LearningResource, SoftwareApplication]:
    metadata = hit.get('metadata', {})
    resource_type = metadata.get('resource_type', {}).get('type','OTHER').upper()

    if resource_type == 'PUBLICATION':
        digitalObj = Article() 
    elif resource_type in ['PRESENTATION', 'POSTER']:
        digitalObj = CreativeWork() 
    elif resource_type == 'DATASET':
        digitalObj = Dataset() 
    elif resource_type == 'VIDEO':
        digitalObj = VideoObject() 
    elif resource_type == 'IMAGE':
        digitalObj = ImageObject() 
    elif resource_type == 'LESSON':
        digitalObj = LearningResource() 
    elif resource_type == 'SOFTWARE':
        digitalObj = SoftwareApplication() 
    elif resource_type == 'OTHER':
        digitalObj = CreativeWork() 
    else:
        utils.log_event(type="info", message=f"{source} - Resource type not defined: {resource_type}")                
        digitalObj = CreativeWork()

    digitalObj.additionalType = resource_type    
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

        files = hit.get('files', [])
        for file in files:
            if file.get("key", "").endswith(".pdf"):
                digitalObj.encoding_contentUrl = file.get("links", {}).get("self", "")

    return digitalObj

@utils.handle_exceptions
def get_publication(source: str, doi: str, source_id: str, publications):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-endpoint', ''),
                                                    identifier=source_id)
    
    if search_result:
        metadata = search_result.get('metadata', {})
        resource_type = metadata.get('resource_type', {}).get('type','OTHER').upper()

        digitalObj = map_digital_obj(source, search_result)

        if resource_type.upper() == 'PUBLICATION':
            publications.append(digitalObj)