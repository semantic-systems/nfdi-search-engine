from objects import thing, Project, Author, Organization
from sources import data_retriever
import utils
from main import app

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

    for hit in hits:
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
        
        results['projects'].append(project)