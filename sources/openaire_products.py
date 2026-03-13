from objects import thing, Article, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
from sources import data_retriever
from config import Config
from typing import Union, Iterable, Dict, Any

from sources.base import BaseSource
from nfdi_search_engine.common.formatting import remove_html_tags

class OpenAIRE_Products(BaseSource):

    SOURCE = 'OPENAIRE - Products'

    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(source=self.SOURCE, 
                                                base_url=Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources)
        
        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        response = raw.get("response", {})
        total_records_found = response.get("header", {}).get("total", "").get("$", "")
        hits = response.get("results", {}).get("result",[])

        total_hits = len(hits)
        self.log_event(type="info", message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}")

        return hits

    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
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
            self.log_event(type="info", message=f"{self.SOURCE} - Resource type not defined: {resource_type}")  
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
            digitalObj.name = remove_html_tags(titles.get("$", ""))
        if isinstance(titles, list):
            for title in titles:
                if title.get("@classid","").upper() == "MAIN TITLE":
                    digitalObj.name = remove_html_tags(title.get("$", ""))

        descriptions = oaf_result.get("description", [])
        if isinstance(descriptions, dict):
            digitalObj.description = remove_html_tags(str(descriptions.get("$", "")))
        if isinstance(descriptions, list):
            for description in descriptions:
                digitalObj.description += remove_html_tags(str(description.get("$", ""))) + "<br/>"

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
            _author.additionalType = 'Person'
            _author.name = authors.get("$", "")
            _author.identifier = authors.get("@orcid_pending", "")
            if ";" not in _author.name:
                digitalObj.author.append(_author) 
            else: # author instance is a list however for this record all the authors are combined into one
                for name in _author.name.split(';'):
                    digitalObj.author.append(
                        Author(
                            name=name,
                            additionalType='Person',
                        )
                    )
        if isinstance(authors, list):
            for author in authors:
                _author = Author()
                _author.additionalType = 'Person'
                _author.name = author.get("$", "")
                _author.identifier = author.get("@orcid_pending", "")
                author_source = thing(
                    name=self.SOURCE,
                    identifier=_author.identifier,
                )
                _author.source.append(author_source)
                digitalObj.author.append(_author)  

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("header", {}).get("dri:objIdentifier", {}).get("$", "")
        _source.url = digitalObj.url                   
        digitalObj.source.append(_source)  

        if resource_type == 'PUBLICATION':
            digitalObj.abstract = digitalObj.description

        return digitalObj

    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        for hit in hits:
            digitalObj = self.map_hit(hit)

            metadata = hit.get('metadata', {}).get("oaf:entity", {})
            resource_type = metadata.get('oaf:result', {}).get('resulttype', {}).get("@classname", "OTHER").upper()

            if resource_type == 'PUBLICATION':
                results['publications'].append(digitalObj)
            elif resource_type in ['DATASET', 'SOFTWARE']:                
                results['resources'].append(digitalObj)                
            else:
                results['others'].append(digitalObj)   

    def get_publication(self, doi: str):
        search_result = data_retriever.retrieve_object(source=self.SOURCE, 
                                                        base_url=Config.DATA_SOURCES[self.SOURCE].get('get-publication-endpoint', ''),
                                                        identifier=doi)
        response = search_result.get("response", {})
        total_records_found = response.get("header", {}).get("total", "").get("$", "")
        hits = response.get("results", {}).get("result",[])
        total_hits = len(hits)
        self.log_event(type="info", message=f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}")

        if int(total_hits) > 1:   
            self.log_event(type="info", message=f"{self.SOURCE} - more than 1 record returned against a doi")
            return None
        
        if int(total_hits) > 0:
            for hit in hits:
                digitalObj = self.map_hit(hit)

                metadata = hit.get('metadata', {}).get("oaf:entity", {})
                resource_type = metadata.get('oaf:result', {}).get('resulttype', {}).get("@classname", "OTHER").upper()

                if resource_type.upper() == 'PUBLICATION':
                    return digitalObj
        
        return None


def search(source_name: str, search_term: str, results: dict, failed_sources: list, tracking=None):
    """
    Entrypoint to search OpenAIRE products.
    """
    OpenAIRE_Products(tracking).search(source_name, search_term, results, failed_sources)


def get_publication(source, doi, source_id, publications, tracking=None) -> None:
    
    publication = OpenAIRE_Products(tracking).get_publication(doi)

    if publication:
        publications.append(publication)
