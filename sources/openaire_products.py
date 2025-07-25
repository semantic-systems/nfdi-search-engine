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

    response = search_result.get("response", {})
    total_records_found = response.get("header", {}).get("total", "").get("$", "")
    hits = response.get("results", {}).get("result",[])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")

    if int(total_hits) > 0:   
        for hit in hits:
            digitalObj = map_digital_obj(source, hit)

            metadata = hit.get('metadata', {}).get("oaf:entity", {})
            resource_type = metadata.get('oaf:result', {}).get('resulttype', {}).get("@classname", "OTHER").upper()

            if resource_type == 'PUBLICATION':
                results['publications'].append(digitalObj)
            elif resource_type in ['DATASET', 'SOFTWARE']:                
                results['resources'].append(digitalObj)                
            else:
                results['others'].append(digitalObj)   

# @utils.handle_exceptions
def map_digital_obj(source: str, hit: dict) -> Union[Article, CreativeWork, Dataset, SoftwareApplication]:
    metadata = hit.get('metadata', {}).get("oaf:entity", {})
    resource_type = metadata.get('oaf:result', {}).get('resulttype', {}).get("@classname", "OTHER").upper()
    # print("Resource Type:", resource_type)

    if resource_type == 'PUBLICATION':
        digitalObj = Article() 
    elif resource_type == 'SOFTWARE':
        digitalObj = SoftwareApplication() 
    elif resource_type == 'DATASET':
        digitalObj = Dataset()                   
    elif resource_type.upper() == 'OTHER':
        digitalObj = CreativeWork() 
    else:
        utils.log_event(type="info", message=f"{source} - Resource type not defined: {resource_type}")  
        digitalObj = CreativeWork()

    digitalObj.additionalType = resource_type

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
        # Add direct PDF URL if access is open
        access_right = children_instance.get('accessright', {}).get('@classid', '').upper()
        pdf_url = children_instance.get('webresource', {}).get('url', {}).get('$', '')
        if access_right in ['OPEN', 'OPEN ACCESS'] and pdf_url.endswith('.pdf'):
            digitalObj.encoding_contentUrl = pdf_url
    if isinstance(children_instance, list):
        digitalObj.url = next(iter(children_instance)).get('webresource', {}).get('url', {}).get('$', '')
        # Add direct PDF URL if access is open
        first_instance = next(iter(children_instance))
        access_right = first_instance.get('accessright', {}).get('@classid', '').upper()
        pdf_url = first_instance.get('webresource', {}).get('url', {}).get('$', '')
        if access_right in ['OPEN', 'OPEN ACCESS'] and pdf_url.endswith('.pdf'):
            digitalObj.encoding_contentUrl = pdf_url
                            
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
        if ";" not in _author.name:
            digitalObj.author.append(_author) 
        else: # author instance is a list however for this record all the authors are combined into one 
            utils.split_authors(_author.name, ";", digitalObj.author)
    if isinstance(authors, list): 
        for author in authors:
            _author = Author()
            _author.type = 'Person'
            _author.name = author.get("$", "")
            _author.identifier = author.get("@orcid_pending", "")
            author_source = thing(
                name=source,
                identifier=_author.identifier,
            )
            _author.source.append(author_source)
            digitalObj.author.append(_author)  

    _source = thing()
    _source.name = source
    _source.identifier = hit.get("header", {}).get("dri:objIdentifier", {}).get("$", "")
    _source.url = digitalObj.url                   
    digitalObj.source.append(_source)  

    if resource_type == 'PUBLICATION':
        digitalObj.abstract = digitalObj.description

    return digitalObj


@utils.handle_exceptions
def get_publication(source: str, doi: str, source_id: str, publications):
    search_result = data_retriever.retrieve_object(source=source, 
                                                    base_url=app.config['DATA_SOURCES'][source].get('get-publication-endpoint', ''),
                                                    identifier=doi)
    response = search_result.get("response", {})
    total_records_found = response.get("header", {}).get("total", "").get("$", "")
    hits = response.get("results", {}).get("result",[])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_hits}")

    if int(total_hits) > 1:   
        utils.log_event(type="info", message=f"{source} - more than 1 record returned against a doi")
        return
    
    if int(total_hits) > 0:   
        for hit in hits:
            digitalObj = map_digital_obj(source, hit)

            metadata = hit.get('metadata', {}).get("oaf:entity", {})
            resource_type = metadata.get('oaf:result', {}).get('resulttype', {}).get("@classname", "OTHER").upper()

            if resource_type.upper() == 'PUBLICATION':
                publications.append(digitalObj)