from nfdi_search_engine.common.models.objects import thing, Article, Author, CreativeWork, Dataset, SoftwareApplication, VideoObject, ImageObject, LearningResource
from sources import data_retriever
from config import Config
from typing import Union, Iterable, Dict, Any
from urllib.parse import quote

from sources.base import BaseSource
from nfdi_search_engine.common.formatting import remove_html_tags


class OpenAIRE_Products(BaseSource):

    SOURCE = 'OPENAIRE - Products'

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        search_result = data_retriever.retrieve_data(
            base_url=Config.DATA_SOURCES[self.SOURCE].get(
                'search-endpoint', ''),
            search_term=search_term,
        )

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
                if title.get("@classid", "").upper() == "MAIN TITLE":
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
            else:  # author instance is a list however for this record all the authors are combined into one
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

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term)
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
        search_result = data_retriever.retrieve_object(
            base_url=Config.DATA_SOURCES[self.SOURCE].get('get-publication-endpoint', ''),
            identifier=doi
        )
        response = search_result.get("response", {})
        total_records_found = response.get("header", {}).get("total", "").get("$", "")
        hits = response.get("results", {}).get("result", [])
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

    def get_resource(self, identifier: str):
        """
        Retrieve detailed information for a single OpenAIRE resource.
        Uses OpenAIRE Graph API by OpenAIRE id.
        """
        endpoint = Config.DATA_SOURCES[self.SOURCE].get('get-resource-endpoint', '')
        if not endpoint:
            self.log_event(type="error", message=f"{self.SOURCE} - get-resource-endpoint is missing")
            return None

        graph_item = data_retriever.retrieve_data(
            base_url="",
            search_term="",
            url=f"{endpoint}{quote(identifier, safe='')}",
            quote=False,
        )

        resource_type = str(graph_item.get("type", "")).upper()
        if resource_type not in ["DATASET", "SOFTWARE"]:
            self.log_event(
                type="error",
                message=f"{self.SOURCE} - detail record is not a resource type: {resource_type}",
            )
            return None

        digital_obj = Dataset() if resource_type == "DATASET" else SoftwareApplication()
        digital_obj.additionalType = resource_type

        # prefer DOI pid as canonical identifier, fallback to OpenAIRE id
        pids = graph_item.get("pids", []) or []
        doi_pid = next((p.get("value", "") for p in pids if str(p.get("scheme", "")).lower() == "doi"), "")
        digital_obj.identifier = doi_pid or graph_item.get("id", "")
        digital_obj.name = graph_item.get("mainTitle", "")

        descriptions = graph_item.get("descriptions", []) or []
        if descriptions:
            digital_obj.description = remove_html_tags(str(descriptions[0]))
            digital_obj.abstract = digital_obj.description

        digital_obj.datePublished = graph_item.get("publicationDate", "")
        digital_obj.license = (graph_item.get("bestAccessRight", {}) or {}).get("label", "")

        language = graph_item.get("language")
        if language:
            if isinstance(language, str):
                digital_obj.inLanguage.append(language)
            elif isinstance(language, dict):
                lang_val = language.get("value") or language.get("label") or language.get("code")
                if lang_val:
                    digital_obj.inLanguage.append(lang_val)

        for subj in (graph_item.get("subjects", []) or []):
            value = (subj.get("subject", {}) or {}).get("value", "")
            if value:
                digital_obj.keywords.append(value)

        for a in (graph_item.get("authors", []) or []):
            person = Author()
            person.additionalType = "Person"
            person.name = a.get("fullName", "") or " ".join(filter(None, [a.get("name", ""), a.get("surname", "")])).strip()
            pid = a.get("pid", {}) or {}
            person.identifier = (pid.get("id", {}) or {}).get("value", "")
            if person.name:
                digital_obj.author.append(person)

        urls = []
        for inst in (graph_item.get("instances", []) or []):
            urls.extend(inst.get("urls", []) or [])
        if urls:
            digital_obj.url = urls[0]

        src = thing()
        src.name = self.SOURCE
        src.identifier = graph_item.get("id", identifier)
        src.url = digital_obj.url
        digital_obj.source.append(src)

        self.log_event(type="info", message=f"{self.SOURCE} - retrieved resource details")
        return digital_obj


def search(search_term: str, results: dict, tracking=None):
    """
    Entrypoint to search OpenAIRE products.
    """
    OpenAIRE_Products(tracking).search(search_term, results)


def get_publication(doi, publications, tracking=None) -> None:

    publication = OpenAIRE_Products(tracking).get_publication(doi)

    if publication:
        publications.append(publication)


def get_resource(doi: str, tracking=None):
    return OpenAIRE_Products(tracking).get_resource(doi)
