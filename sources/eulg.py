import urllib
from typing import List, Dict, Any, Iterable

import requests

import utils
from elg import Catalog
from main import app
from objects import Dataset, SoftwareApplication
from sources.base import BaseSource


class EULG(BaseSource):
    """
    Implements the BaseSource interface for the European Language Grid (ELG / EULG).
    """
    SOURCE = "EULG"

    class _CatalogWithTimeout(Catalog):
        def _get(self, path: str, queries: List[set] = [], json: bool = False):
            url = (
                "https://live.european-language-grid.eu/catalogue_backend/api/registry/"
                + path
                + ("?" if len(queries) >= 1 else "")
                + "&".join(
                    [
                        f"{query}={urllib.parse.quote_plus(str(value))}"
                        for (query, value) in queries
                    ]
                )
            )
            response = requests.get(url, timeout=int(app.config["REQUEST_TIMEOUT"]))
            return response.json() if json else response

    def fetch(self, search_term: str, failed_sources) -> Dict[str, Any]:
        """
        For ELG, we don't have a single JSON "search endpoint" returning hits in one response
        (as in Elastic-style APIs). Instead we call the ELG python client and return a raw dict
        that our extract_hits() understands.
        """
        catalog = self._CatalogWithTimeout()

        resource_items = ["Corpus", "Tool/Service", "Lexical/Conceptual resource"]
        all_results = []
        for resource_item in resource_items:
            try:
                elg_results = catalog.search(
                    resource=resource_item,
                    search=search_term,
                    limit=100,
                )
                all_results.extend(elg_results or [])
            except Exception:
                if failed_sources is not None:
                    failed_sources.append(self.SOURCE)
                raise

        # Wrap in a "raw" structure similar to what your pipeline expects
        return {"hits": {"total": len(all_results), "hits": all_results}}

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Any]:
        total_records_found = raw.get("hits", {}).get("total", 0)
        hits = raw.get("hits", {}).get("hits", [])
        total_hits = len(hits)
        message = f"{self.SOURCE} - {total_records_found} records matched; pulled top {total_hits}"
        utils.log_event(type="info", message=message)

        return hits or []

    @staticmethod
    def _first_license(result) -> str:
        if getattr(result, "licences", None):
            return result.licences[0]
        return ""

    @staticmethod
    def _collect_list_or_buckets(value) -> List[str]:
        """
        ELG sometimes returns lists, sometimes bucket-like dicts.
        This normalizes to a flat list of strings.
        """
        out: List[str] = []

        if isinstance(value, list):
            for item in value:
                for part in str(item).split(","):
                    part = part.strip()
                    if part:
                        out.append(part)
            return out

        if isinstance(value, dict):
            for bucket in value.get("buckets", []):
                for entry in bucket:
                    k = entry.get("key")
                    if k:
                        out.append(str(k))
            return out

        return out

    @utils.handle_exceptions
    def map_hit(self, hit: Any) -> Any:
        """
        Map a single ELG result object to one of our objects.py classes.
        ELG hits here are objects returned by the ELG python client, not dicts.
        """
        result = hit
        resource_type = getattr(result, "resource_type", "")

        description = utils.remove_html_tags(getattr(result, "description", "") or "")
        first_license = self._first_license(result)

        if resource_type in ("Corpus", "Lexical/Conceptual resource"):
            url = ""
            if resource_type == "Corpus":
                url = f"https://live.european-language-grid.eu/catalogue/corpus/{result.id}"
            elif resource_type == "Lexical/Conceptual resource":
                url = f"https://live.european-language-grid.eu/catalogue/lcr/{result.id}"

            dataset = Dataset()
            dataset.source = "elg:corpus"
            dataset.name = getattr(result, "resource_name", "")
            dataset.url = url
            dataset.datePublished = str(getattr(result, "creation_date", ""))
            dataset.description = description
            dataset.license = first_license
            dataset.countryOfOrigin = getattr(result, "country_of_registration", "")

            for kw in self._collect_list_or_buckets(getattr(result, "keywords", None)):
                dataset.keywords.append(kw)
            for lang in self._collect_list_or_buckets(getattr(result, "languages", None)):
                dataset.inLanguage.append(lang)

            return dataset

        if resource_type == "Tool/Service":
            software = SoftwareApplication()
            software.source = "elg:software/service"
            software.name = getattr(result, "resource_name", "")
            software.url = f"https://live.european-language-grid.eu/catalogue/tool-service/{result.id}"
            software.description = description
            software.datePublished = str(getattr(result, "creation_date", ""))
            software.countryOfOrigin = getattr(result, "country_of_registration", "")
            software.license = first_license

            for kw in self._collect_list_or_buckets(getattr(result, "keywords", None)):
                software.keywords.append(kw)
            for lang in self._collect_list_or_buckets(getattr(result, "languages", None)):
                software.inLanguage.append(lang)

            return software

        return None

    @utils.handle_exceptions
    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch from ELG, extract hits, map to objects, and insert into results in-place.
        """
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw)

        for hit in hits:
            digital_obj = self.map_hit(hit)
            if digital_obj is None:
                continue

            if isinstance(digital_obj, Dataset):
                results["resources"].append(digital_obj)
            elif isinstance(digital_obj, SoftwareApplication):
                results["resources"].append(digital_obj)
            else:
                results.setdefault("others", []).append(digital_obj)


def search(source_name: str, search_term: str, results: dict, failed_sources: list):
    """
    Entrypoint to search EULG/ELG.
    """
    EULG().search(source_name, search_term, results, failed_sources)


# from objects import Dataset, SoftwareApplication
# import utils
# from elg import Catalog
#
# import urllib
# from typing import List
# import requests
# from main import app
#
# import logging
# logger = logging.getLogger('nfdi_search_engine')
#
# @utils.timeit
# def search(search_term, results):
#
#     class Catalog_with_timeout_parameter(Catalog):
#         def _get(self, path: str, queries: List[set] = [], json: bool = False):
#             """
#             Internal method to call the API
#             """
#             try:
#                 url = (
#                     "https://live.european-language-grid.eu/catalogue_backend/api/registry/"
#                     + path
#                     + ("?" if len(queries) >= 1 else "")
#                     + "&".join([f"{query}={urllib.parse.quote_plus(str(value))}" for (query, value) in queries])
#                 )
#                 response = requests.get(url, timeout=int(app.config["REQUEST_TIMEOUT"]))
#                 # ensure_response_ok(response)
#                 if json:
#                     return response.json()
#                 return response
#
#             except requests.exceptions.Timeout as ex:
#                 raise ex
#
#             except Exception as ex:
#                 raise ex
#
#
#
#     catalog = Catalog_with_timeout_parameter()
#     resource_items = ["Corpus", "Tool/Service", "Lexical/Conceptual resource"]  # "Language description"]
#     for resource_item in resource_items:
#         elg_results = catalog.search(
#             resource=resource_item,  # languages = ["English","German"], # string or list if multiple languages
#             search=search_term,
#             limit=100,
#         )
#         for result in elg_results:
#             description = result.description
#
#             first_license: str = ''
#             if result.licences:
#                 first_license = result.licences[0]
#
#             description = utils.remove_html_tags(description)
#             if result.resource_type == 'Corpus' or result.resource_type == 'Lexical/Conceptual resource':
#                 url = ''
#                 if result.resource_type == 'Corpus':
#                     url = 'https://live.european-language-grid.eu/catalogue/corpus/' + str(result.id)
#                 if result.resource_type == 'Lexical/Conceptual resource':
#                     url = 'https://live.european-language-grid.eu/catalogue/lcr/' + str(result.id)
#
#                 dataset = Dataset()
#                 dataset.source = 'elg:corpus'
#                 dataset.name = result.resource_name
#                 dataset.url = url
#                 dataset.datePublished = str(result.creation_date)
#                 dataset.description = description
#                 keywords = result.keywords
#                 if isinstance(keywords, list):
#                     for keyword in keywords:
#                         for key in keyword.split(","):
#                             dataset.keywords.append(key)
#                 elif isinstance(keywords, dict):
#                     for keyword in keywords.get('buckets', []):
#                         for items in keyword:
#                             dataset.keywords.append(items['key'])
#                 else:
#                     dataset.keywords.append('')
#
#                 languages = result.languages
#                 if isinstance(languages, list):
#                     for language in languages:
#                         for key in language.split(","):
#                             dataset.inLanguage.append(key)
#                 elif isinstance(languages, dict):
#                     for language in languages.get('buckets', []):
#                         for items in language:
#                             dataset.inLanguage.append(items['key'])
#                 else:
#                     dataset.inLanguage.append('')
#
#                 # dataset.license = ', '.join(str(licence) for licence in result.licences)
#                 dataset.license = first_license
#                 dataset.countryOfOrigin = result.country_of_registration
#                 results['resources'].append(dataset)
#                 '''
#                 results.append(
#                     Dataset(
#                         title=result.resource_name,
#                         authors=result.resource_type,
#                         url=url,
#                         description=description,
#                         date=result.creation_date
#                     )
#                 )
#                 '''
#             elif result.resource_type == "Tool/Service":
#                 software = SoftwareApplication()
#                 url = "https://live.european-language-grid.eu/catalogue/tool-service/" + str(result.id)
#                 description = result.description
#                 description = utils.remove_html_tags(description)
#                 software.source = 'elg:software/service'
#                 software.name = result.resource_name
#                 software.url = url
#                 software.description = description
#                 software.datePublished = str(result.creation_date)
#                 software.countryOfOrigin = result.country_of_registration
#                 keywords = result.keywords
#                 if isinstance(keywords, list):
#                     for keyword in keywords:
#                         for key in keyword.split(","):
#                             software.keywords.append(key)
#                 elif isinstance(keywords, dict):
#                     for keyword in keywords.get('buckets', []):
#                         for items in keyword:
#                             software.keywords.append(items['key'])
#                 else:
#                     software.keywords.append('')
#
#                 languages = result.languages
#                 if isinstance(languages, list):
#                     for language in languages:
#                         for key in language.split(","):
#                             software.inLanguage.append(key)
#                 elif isinstance(languages, dict):
#                     for language in languages.get('buckets', []):
#                         for items in language:
#                             software.inLanguage.append(items['key'])
#                 else:
#                     software.inLanguage.append('')
#
#                 # software.license = ', '.join(str(licence) for licence in result.licences)
#                 software.license = first_license
#                 results['resources'].append(software)
#                 '''
#                 results.append(
#                     Software(
#                         url=url,
#                         title=result.resource_name,
#                         authors=result.resource_type,
#                         date=result.creation_date,
#                         description=description,
#                         version=', '.join(str(licence) for licence in result.licences)
#                     )
#                 )
#                 '''
#                 # languages=', '.join(str(language) for language in result.languages)