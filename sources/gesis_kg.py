from objects import thing, Article, Author
from sources import data_retriever
import utils
from main import app
from string import Template
from datetime import datetime
from dateutil import parser


@utils.handle_exceptions
def search(source: str, search_term: str, results, failed_sources):
    query_template = Template('''
                            PREFIX schema:<https://schema.org/>
                            PREFIX rdfs:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                            
                            SELECT ?publication ?title (GROUP_CONCAT(DISTINCT ?abstract; SEPARATOR=", ") AS ?abstracts)
                                    (GROUP_CONCAT(DISTINCT ?linksURN; SEPARATOR=", ") AS ?linksURNs) 
                                    (GROUP_CONCAT(DISTINCT ?url; SEPARATOR=", ") AS ?urls)
                                    (GROUP_CONCAT(DISTINCT ?datePublished; SEPARATOR=", ") AS ?datePublisheds)
                                    (GROUP_CONCAT(DISTINCT ?contributor_name; SEPARATOR="; ") AS ?contributors)
                                    (GROUP_CONCAT(DISTINCT ?author_name; SEPARATOR="; ") AS ?authors)
                                    (GROUP_CONCAT(DISTINCT ?provider; SEPARATOR=", ") AS ?providers)
                                    (GROUP_CONCAT(DISTINCT ?inLanguage; SEPARATOR=", ") AS ?languages)
                                    (GROUP_CONCAT(DISTINCT ?sourceInfo; SEPARATOR=", ") AS ?sourceInfos)
                            WHERE {
                                ?publication rdfs:type schema:ScholarlyArticle .
                                ?publication schema:name ?title . FILTER(CONTAINS(?title, "$search_string"))
                                
                                OPTIONAL { ?publication schema:abstract ?abstract . }
                                OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/linksURN> ?linksURN . }
                                OPTIONAL { ?publication schema:url ?url . }
                                OPTIONAL { ?publication schema:datePublished ?datePublished . }
                                OPTIONAL { ?publication schema:provider ?provider . }
                                OPTIONAL { ?publication schema:inLanguage ?inLanguage . }
                                OPTIONAL { ?publication <https://data.gesis.org/gesiskg/schema/sourceInfo> ?sourceInfo . }
                                OPTIONAL { ?publication schema:contributor ?contributor . 
                                            ?contributor schema:name ?contributor_name .}
                                OPTIONAL { ?publication schema:author ?author .
                                           ?author schema:name ?author_name . }
                            }
                            GROUP BY ?publication ?title
                            LIMIT $number_of_records
                            ''')

    replacement_dict = {
        "search_string": search_term,
        "number_of_records": app.config['NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT']
    }
    query = query_template.substitute(replacement_dict)
    query = ' '.join(query.split())
    # print(query)
    search_result = data_retriever.retrieve_data(source=source,
                                                 base_url=app.config['DATA_SOURCES'][source].get('search-endpoint', ''),
                                                 search_term=query,
                                                 failed_sources=failed_sources)

    hits = search_result.get("results", {}).get("bindings", [])
    # print(hits)
    total_hits = len(hits)
    utils.log_event(type="info", message=f"{source} - {total_hits} records matched; pulled top {total_hits}")
    print(total_hits)
    if int(total_hits) > 0:
        for hit in hits:
            # print(hit)
            publication = Article()

            publication.name = hit.get("title", {}).get("value", "")
            print(publication.name)
            # publication.url = hit.get("urls", {}).get("value", "")
            # print(publication.url)
            publication.identifier = hit.get("linksURNs", {}).get("value", "")  # DOI is available for few; we need to update the sparql query to fetch this information
            print(publication.identifier)
            publication.datePublished = datetime.strftime(parser.parse(hit.get('date', {}).get('value', "")),
                                                          '%Y-%m-%d')
            print(publication.datePublished)
            publication.inLanguage = hit.get("languages", {}).get("value", "")
            print(publication.inLanguage)
            #publication.sourceOrganization = hit.get("providers", {}).get("value", "")
            publication.abstract = hit.get("abstracts", {}).get("value", "")
            publication.publisher = hit.get("sourceInfos", {}).get("value", "")

            authors = hit.get("authors", {}).get("value", "")
            contributors = hit.get("contributors", {}).get("value", "")
            authors_list = authors.rstrip(",").split(";")
            for contributor in contributors.rstrip(",").split(";"):
                if contributor not in authors_list:
                    authors_list.append(contributor)
            print(authors_list)
            for authorsName in authors_list: #authors.rstrip(",").split(";"):
                _author = Author()
                _author.type = 'Person'
                _author.name = authorsName
                _author.identifier = ""  # ORCID is available for few; we need to update the sparql query to pull this information
                publication.author.append(_author)

            # authorsStrings = hit.get("authorsString", {}).get("value", "")
            # for authorsString in authorsStrings.rstrip(",").split(","):
            #     _author = Author()
            #     _author.type = 'Person'
            #     _author.name = authorsString
            #     _author.identifier = ""
            #     publication.author.append(_author)

            _source = thing()
            _source.name = 'GESIS KG'
            _source.identifier = hit['publication'].get('value', "") #.replace("http://www.wikidata.org/", "")  # remove the base url and only keep the ID
            # _source.url = hit['item'].get('value', "")
            publication.source.append(_source)

            # if publication.identifier != "":
            #     results['publications'].append(publication)
            # else:
            results['others'].append(publication)


def search_gesis_kg(search_string):
    sparql = """PREFIX schema:<https://schema.org/>
            PREFIX rdfs:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT *
            WHERE {
                ?publication rdfs:type schema:ScholarlyArticle .
                ?publication schema:name ?name .
                FILTER(CONTAINS(?name, "In Search of the Finnish New Middle Class"))
                ?publication schema:publicationType ?publicationType.
                FILTER(lang(?publicationType) = "en")
                ?publication schema:author ?author ;
                             schema:contributor ?contributor ;
                             schema:inLanguage ?language ;
                             schema:provider ?provider ;
                             schema:url ?url ;
                             schema:datePublished ?datePublished ;
                             schema:abstract ?abstract;
                             schema:issn	?issn;
                             schema:issueNumber ?issueNumber ;
                             schema:volumeNumber ?volumeNumber ;	
                             schema:provider ?provider ;
                             <https://data.gesis.org/gesiskg/schema/linksURN> ?linksURN .
            }
    """
    sparql_query = f"""
    PREFIX schema:<https://schema.org/>;
    PREFIX rdfs:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>;
    SELECT *
    WHERE {{
        ?publication rdfs:type schema:ScholarlyArticle .
        ?publication schema:name ?name .
        FILTER(CONTAINS(?name, "{search_string}"))
        ?publication ?p ?o .
    }}
    """
