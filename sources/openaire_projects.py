from nfdi_search_engine.common.models.objects import thing, Project, Author, Organization
from sources import data_retriever
from typing import Iterable, Dict, Any
from config import Config

from sources.base import BaseSource

class OpenAIRE_Projects(BaseSource):

    SOURCE = 'OPENAIRE - Projects'

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        return data_retriever.retrieve_data(
            base_url=Config.DATA_SOURCES[self.SOURCE].get('search-endpoint', ''),
            search_term=search_term,
        )

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

    def map_hit(self, hit: Dict[str, Any]) -> Project:
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        pro_result = hit.get('metadata', {}).get('oaf:entity', {}).get('oaf:project', {})
        
        project = Project()     
        project.identifier = pro_result.get('code', {}).get('$', '')   
        project.name = pro_result.get('title', {}).get('$', '')
        project.dateStart = pro_result.get('startdate', {}).get('$', '')
        project.dateEnd = pro_result.get('enddate', {}).get('$', '')
        project.duration = pro_result.get('duration', {}).get('$', '')
        project.description = pro_result.get('summary', {}).get('$', '')
        project.currency = pro_result.get('currency', {}).get('$', '')
        project.totalCost = "{:,.2f}".format(float(pro_result.get('totalcost', {}).get('$', '')))
        project.fundedAmount = "{:,.2f}".format(float(pro_result.get('fundedamount', {}).get('$', '')))

        # # fundingtree can be dict or list
        # # fundingtree = pro_result.get('fundingtree', {}) if pro_result.get('fundingtree') is not None else {}
        # fundingtree = pro_result.get('fundingtree', None)
        # if type(fundingtree) is dict:
        #     orga = Organization()
        #     orga.name = fundingtree.get('name', {}).get('$', '')
        #     project.funder.append(orga)
        # elif type(fundingtree) is list:
        #     for item in fundingtree:
        #         orga = Organization()
        #         orga.name = item.get('name', {}).get('$', '')
        #         project.funder.append(orga)

        # # "rels" can be None, dict, list
        # relations = pro_result.get('rels', {}).get('rel', {}) if pro_result.get('rels', {}) is not None else []
        # if type(relations) is dict:
        #     relations = [relations]

        # # This need a review. Type 'Organization' ?
        # for rel in relations:
        #     author_obj = Author()
        #     author_obj.additionalType = 'Organization'
        #     author_obj.name = (rel.get('legalname', {}).get('$', ''))
        #     project.author.append(author_obj)
        
        _source = thing()
        _source.name = 'OPENAIRE'
        _source.identifier = hit.get("header", {}).get("dri:objIdentifier", {}).get("$", "")
        # _source.url = digitalObj.url                   
        project.source.append(_source)

        return project

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        raw = self.fetch(search_term)
        hits = self.extract_hits(raw)

        for hit in hits:
            project = self.map_hit(hit)
            results['projects'].append(project)


def search(search_term: str, results, tracking=None): 
    """
    Entrypoint to search OpenAIRE Projects.
    """
    OpenAIRE_Projects(tracking).search(search_term, results)
