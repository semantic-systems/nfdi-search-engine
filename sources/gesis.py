
from objects import thing, Dataset, Author
from sources import data_retriever
import utils
from main import app

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)      
        
    total_records_found = search_result.get('hits', {}).get('total', '')
    total_hits = search_result.get('hits', {}).get('hits', [])
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {len(total_hits)}")    
    for hit in total_hits:
        # Extract the dc fields from the hit object
        dc_fields = hit['_source']['dc']
        digital_obj = Dataset()
        digital_obj.additionalType = 'DATASET' # change it to the specific type if returned from Gesis        
        # doi = dc_fields['relation']['nn'][0] if 'relation' in dc_fields and 'nn' in dc_fields['relation'] else 'Unknown DOI'
        identifier_list = dc_fields.get('identifier', {}).get('nn', [])
        if len(identifier_list) > 0:
            digital_obj.identifier = identifier_list[0].replace('https://doi.org/','')
        title = dc_fields['title']['all'][0] if 'title' in dc_fields and 'all' in dc_fields['title'] else ''
        digital_obj.name =title 
        description = dc_fields['description']['all'][0] if 'description' in dc_fields and 'all' in dc_fields['description'] else ''
        short_description = utils.remove_html_tags(description)
        digital_obj.abstract = short_description
        digital_obj.description = short_description
        type = dc_fields['type']['all'][0] if 'type' in dc_fields and 'all' in dc_fields['type'] else 'Type not available'
        date_published = dc_fields['date']['nn'][0] if 'date' in dc_fields and 'nn' in dc_fields['date'] else ''
        digital_obj.datePublished = date_published
        publisher = dc_fields['publisher']['all'][0] if 'publisher' in dc_fields and 'all' in dc_fields['publisher'] else None
        digital_obj.publisher=publisher
        rights = dc_fields['rights']['all'][0] if 'rights' in dc_fields and 'all' in dc_fields['rights'] else None
        digital_obj.license = rights
        languages = dc_fields['language']['all'] if 'language' in dc_fields and 'all' in dc_fields['language'] else ''
        if languages:
            for language in languages:
                digital_obj.inLanguage.append(language)
        
        for creator in dc_fields.get('creator', {}).get("all", []):
            author = Author()
            author.additionalType = "Person" # there is not type for creator in Gesis it's jus for now
            author.name = creator
            digital_obj.author.append(author)

        digital_obj.originalSource = hit['_source'].get('setUrl', '')  

        
        id = hit['_id']
        id = id.replace('.', '-')
        url = f"https://search.gesis.org/research_data/datasearch-{id}"

        if len(identifier_list) > 1:
            gesis_identifier = identifier_list[1].replace('ZA-No.: ','')
            url = f"https://search.gesis.org/research_data/{gesis_identifier}"

        digital_obj.url=url

        _source = thing()
        _source.name = 'GESIS'
        _source.identifier = digital_obj.identifier
        _source.url = digital_obj.url
                          
        digital_obj.source.append(_source)


        results['resources'].append(digital_obj)

       


