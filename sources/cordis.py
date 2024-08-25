from objects import thing, Project, Author
from sources import data_retriever
import utils
from main import app

@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources): 
    search_term = f"({search_term})"
    search_result = data_retriever.retrieve_data(source=source, 
                                                base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                search_term=search_term,
                                                failed_sources=failed_sources) 
    total_records_found = search_result.get('result', {}).get('header', {}).get('totalHits', 0)
    total_records_pulled = search_result.get('result', {}).get('header', {}).get('numHits', 0)
    utils.log_event(type="info", message=f"{source} - {total_records_found} records matched; pulled top {total_records_pulled}")   

    hits = search_result.get('hits', {}).get('hit', [])
    for hit in hits:
        if isinstance(hit, dict):
            projectNode = hit.get('project', {})
            type = projectNode.get('contenttype', '')

            if type == "project":
                project = Project()
                project.identifier = projectNode.get('identifiers', {}).get('grantDoi', '')
                project.name = projectNode.get('title', '')
                project.alternateName = projectNode.get('acronym', '')
                project.url = f"https://cordis.europa.eu/project/id/{projectNode.get('id', '')}"
                project.dateStart = projectNode.get('startDate', '')
                project.dateEnd = projectNode.get('endDate', '')
                project.duration = projectNode.get('duration', '')                
                project.datePublished = projectNode.get('ecSignatureDate', '')                
                project.description = projectNode.get("objective", '')
                project.status = projectNode.get("status", '')
                project.totalCost = "{:,.2f}".format(float(projectNode.get('totalCost', '')))
                project.eu_contribution = "{:,.0f}".format(float(projectNode.get('ecMaxContribution', '')))

                keywords = projectNode.get("keywords", None)
                if keywords:
                    for keyword in keywords:
                        project.keywords.append(keyword)

                languages = projectNode.get("language", None)
                if languages:
                    if isinstance(languages, list):
                        # If languages is a list, add each language to project.inLanguage
                        for language in languages:
                            project.inLanguage.append(language)
                    else:
                        # If languages is a single string, directly append it to project.inLanguage
                        project.inLanguage.append(languages)                

                _source = thing()
                _source.name = 'CORDIS'
                _source.identifier = projectNode.get('id', '')
                _source.url = project.url                        
                project.source.append(_source)


                results['projects'].append(project)
    
