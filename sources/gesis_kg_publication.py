from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app
from string import Template


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    query_template = Template('''
                            PREFIX schema:<https://schema.org/>
                            PREFIX rdfs:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                            
                            SELECT ?publication ?title ?doi ?abstract
                                    (GROUP_CONCAT(DISTINCT ?linksURN; SEPARATOR=", ") AS ?linksURNs) 
                                    (GROUP_CONCAT(DISTINCT ?url; SEPARATOR=", ") AS ?urls)
                                    (GROUP_CONCAT(DISTINCT ?datePub; SEPARATOR=", ") AS ?datePublished)
                                    (GROUP_CONCAT(DISTINCT ?contributor_name; SEPARATOR="; ") AS ?contributors)
                                    (GROUP_CONCAT(DISTINCT ?author_name; SEPARATOR="; ") AS ?authors)
                                    (GROUP_CONCAT(DISTINCT ?provider; SEPARATOR=", ") AS ?providers)
                                    (GROUP_CONCAT(DISTINCT ?inLanguage; SEPARATOR=", ") AS ?languages)
                                    (GROUP_CONCAT(DISTINCT ?sourceInfo; SEPARATOR=", ") AS ?sourceInfos)
                            WHERE {
                                ?publication rdfs:type schema:ScholarlyArticle .
                                ?publication schema:name ?title . FILTER(CONTAINS(?title, "$search_string"))
                                
                                OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/doi> ?doi . }
                                OPTIONAL { ?publication schema:abstract ?abstract . }
                                OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/linksURN> ?linksURN . }
                                OPTIONAL { ?publication schema:url ?url . }
                                OPTIONAL { ?publication schema:datePublished ?datePub . }
                                OPTIONAL { ?publication schema:provider ?provider . }
                                OPTIONAL { ?publication schema:inLanguage ?inLanguage . }
                                OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/sourceInfo> ?sourceInfo . }
                                OPTIONAL { ?publication schema:contributor ?contributor . 
                                            ?contributor schema:name ?contributor_name .}
                                OPTIONAL { ?publication schema:author ?author .
                                           ?author schema:name ?author_name . }
                            }
                            GROUP BY ?publication ?title ?doi ?abstract
                            LIMIT $number_of_records
                            ''')

    replacement_dict = {
        "search_string": search_term,
        "number_of_records": app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']
    }
    query = query_template.substitute(replacement_dict)
    query = ' '.join(query.split())
    search_result = data_retriever.retrieve_data(source=source,
                                                 base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                 search_term=query,
                                                 failed_sources=failed_sources)

    hits = search_result.get("results", {}).get("bindings", [])
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {total_hits}")
    if int(total_hits) > 0:
        for hit in hits:
            publication = Article()
            publication.identifier = hit.get("doi", {}).get("value", "")
            publication.name = hit.get("title", {}).get("value", "")
            publication.url =  hit.get("urls", {}).get("value", "").strip() #hit.get("urls", {}).get("value", "")

            #publication.identifier = hit.get("linksURNs", {}).get("value", "")  # DOI is available for few; we need to update the sparql query to fetch this information
            publication.description = hit.get("abstract", {}).get("value", "")
            publication.datePublished = hit.get('datePublished', {}).get('value', "")
            languages = hit.get("languages", {}).get("value", "")
            if languages:
                for language in languages.strip().split(" "):
                    publication.inLanguage.append(language)
            #publication.sourceOrganization = hit.get("providers", {}).get("value", "")
            publication.publisher = hit.get("sourceInfos", {}).get("value", "")

            authors = hit.get("authors", {}).get("value", "")
            contributors = hit.get("contributors", {}).get("value", "")
            authors_list = [name for name in (authors + ";" + contributors).strip(", ").split(";") if name ]
            authors_list = list(dict.fromkeys(authors_list))

            for authorsName in authors_list:
                _author = Author()
                _author.type = 'Person'
                _author.name = authorsName
                _author.identifier = ""  # ORCID is available for few; we need to update the sparql query to pull this information
                author_source = thing(
                    name=source,
                    identifier=_author.identifier,
                )
                _author.source.append(author_source)
                publication.author.append(_author)

            _source = thing()
            _source.name = 'GESIS KG'
            _source.originalSource = publication.publisher
            _source.identifier = publication.identifier # hit['publication'].get('value', "") #.replace("http://www.wikidata.org/", "")  # remove the base url and only keep the ID
            _source.url = publication.url #hit['urls'].get('value', "").strip()
            publication.source.append(_source)

            if publication.identifier != "":
                results['publications'].append(publication)
            else:
                results['others'].append(publication)
