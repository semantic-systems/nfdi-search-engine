from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app
import re

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):  
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)           

    total_hits = search_result['hits']['total']['value']
    if int(total_hits) > 0:
        hits = search_result['hits']['hits']    
        utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {len(hits)}")      
        for hit in hits:
            hit_source = hit.get('_source', {})

            publication = Article()                  
            publication.name = hit_source.get("name", "")             
            publication.url = hit_source.get("id", "")  
            publication.identifier =re.sub('^.*doi\.org\/', '', hit_source.get("id", "")) 
            publication.datePublished = utils.parse_date(hit_source.get("datePublished", "")) 
            publication.license = hit_source.get("license", {}).get("id", "")
            
            publication.description = utils.remove_html_tags(hit_source.get("description", ""))
            publication.abstract = publication.description
            # every object is categorized as 'dataset' which seems to be wrong. hence this information should not be used.
            # publication.additionalType = ','.join(hit_source.get("type", [])) 

            publishers = hit_source.get("publisher", [])
            if len(publishers) > 0:
                publication.publication = publishers[0].get("name", "") 

            for author in hit_source.get("creator", []):
                if author['type'] == 'Person':                
                    _author = Author()
                    _author.type = 'Person'
                    _author.name = author.get("name", "")
                    _author.identifier = author.get("id", "").replace('https://orcid.org/','')
                    publication.author.append(_author)    

            _source = thing()
            _source.name = source
            _source.identifier = hit.get("_id", "")
            _source.url = "https://resodate.org/resources/" + hit.get("_id", "")                         
            publication.source.append(_source)

            #information only limited to this source
            publication.image = hit_source.get("image", "")
            keywords = hit_source.get("keywords", None)
            if keywords:
                for keyword in keywords:
                    publication.keywords.append(keyword)

            languages = hit_source.get("inLanguage", None)
            if languages:
                for language in languages:
                    publication.inLanguage.append(language)

            encodings = hit_source.get("encoding", None)
            if encodings:
                for encoding in encodings:
                    publication.encoding_contentUrl = encoding.get("contentUrl", "")
                    publication.encodingFormat = encoding.get("encodingFormat", "")                

            results['publications'].append(publication) 