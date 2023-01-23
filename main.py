import json
import logging
import os
from typing import List

import extruct
import gradio as gr
import requests
from rdflib import Graph, URIRef, RDF
from objects import Person, Zenodo, Article
import search_openalex

logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


def sources(search_term):
    g = Graph()
    results = []
    g, results = dblp(name, g, results)
    g, results = zenodo(name, g, results)
    g, results  = open_alex(name, g, results)

    # TODO add materialized triples via https://github.com/RDFLib/OWL-RL
    g.parse('zenodo2schema.ttl')
    g = g.serialize(format="ttl")

    logger.info(f'Got {len(results)} results')
    return format_results(results)


def format_results(results):
    """From the results obtained from the databases it creates an HTML page, and it returns it

        Args:
            results: List of the different results

        Returns:
            string: single string with the HTML of the results
        """
    formatted_results = """<!DOCTYPE html>
                            <html>
                            <head>
                            <style> 
                                .subtitle  {display: inline; font-size: 20px;}
                                .title  {display: inline; font-size: 30px;} 
                                a  { color: blue;  }
                                .url { color: gray;  }
                                .emoji { font-size:20px }
                                .emoji-title { font-size:30px }
                            </style>
                            </head>
                            <body>"""

    person_result = "<h1 class='title'>Researchers - </h1>" \
                    "<span class='emoji-title'>&#129417;</span>" \
                    "<br><br>"
    exist_person = False

    article_result = "<h1 class='title'>Articles - </h1>" \
                     "<span class='emoji-title'>&#128240;</span>" \
                     "<br><br>"
    exist_article = False

    zenodo_result = "<h1 class='title'>Zenodo - </h1>" \
                    "<span class='emoji-title'>&#128188;</span>" \
                    "<br><br>"
    exist_zenodo = False

    for result in results:
        if isinstance(result, Person):
            person_result += \
                f"<span class='emoji'>&#129417;</span>" \
                f"<h2 class='subtitle'><a href='{result.url}' target='_blank' >{result.name}</a></h2>" \
                f"<p class='faded'>{result.url}</p><br>"
            exist_person = True

        elif isinstance(result, Article):
            if "," in result.url:
                url = result.url.split(',')[0]
            else:
                url = result.url

            article_result +=\
                f"<p class='url'>{result.url}</p>" \
                f"<span class='emoji'>&#128240;</span>" \
                f"<h2 class='subtitle'><a href='{url}' target='_blank'>{result.title}</a></h2>" \
                f" - {result.date}" \
                f"<p>{result.authors}</p>" \
                f"<br>"
            exist_article = True

        elif isinstance(result, Zenodo):
            zenodo_result +=\
                f"<p class='url'>{result.url}</p>" \
                f"<span class='emoji'>&#128188;</span>" \
                f"<h2 class='subtitle'><a href='{result.url}' target='_blank'>{result.title}</a></h2>" \
                f" - {result.date}" \
                f"<p>{result.resource_type}</p>" \
                f"<br>"
            exist_zenodo = True
        else:
            logger.warning(f"Type {type(result)} of result not yet handled")

    # Checking that we have actual results and act accordingly if not
    if not exist_person:
        person_result = ""
    if not exist_article:
        article_result = ""
    if not exist_zenodo:
        zenodo_result = ""
    if not exist_zenodo and not exist_article and not exist_person:
        person_result = "<br><br><h1>No results found </h1><span class='emoji-title'>&#128549;</span>"

    return formatted_results + person_result + article_result + zenodo_result + "</body></html>"


# rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL access token zenodo
def extract_metadata(text: bytes):
    """Extract all metadata present in the page and return a dictionary of metadata lists.

    Args:
        text: The content of a requests.get( ) call

    Returns:
        metadata (dict): Dictionary of json-ld, microdata, and opengraph lists.
        Each of the lists present within the dictionary contains multiple dictionaries.
    """
    metadata = extruct.extract(text,
                               uniform=True,
                               syntaxes=['json-ld',
                                         'microdata',
                                         'opengraph'])
    return metadata


def dblp(search_term: str, g: Graph, results: List):
    headers = {'Accept': 'application/json'}

    response = requests.get(
        'https://dblp.uni-trier.de/search?q=' + search_term,
        headers=headers
    )

    logger.debug(f'DBLP response status code: {response.status_code}')
    logger.debug(f'DBLP response headers: {response.headers}')

    # TODO unclear why here are only a few but now all results returned

    metadata = extract_metadata(response.content)

    # TODO unclear why this loop takes so long
    # PW:
    # The profiler says:
    #          3188239 function calls (3012651 primitive calls) in 18.210 seconds
    #
    #    Ordered by: cumulative time
    #
    #    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
    #        30    0.000    0.000   18.210    0.607 graph.py:1223(parse)
    #        30    0.008    0.000   18.202    0.607 jsonld.py:81(parse)
    #        30    0.000    0.000   18.189    0.606 jsonld.py:118(to_rdf)
    #        30    0.019    0.001   18.189    0.606 jsonld.py:146(parse)
    #        30    0.000    0.000   18.107    0.604 context.py:365(load)
    #     60/30    0.001    0.000   16.618    0.554 context.py:390(_prep_sources)
    #        30    0.001    0.000   16.615    0.554 context.py:430(_fetch_context)
    #        60    0.002    0.000   16.615    0.277 util.py:27(source_to_json)
    #        60    0.001    0.000   13.612    0.227 parser.py:332(create_input_source)
    #        30    0.000    0.000   13.611    0.454 parser.py:436(_create_input_source_from_location)
    #        30    0.003    0.000   13.608    0.454 parser.py:231(__init__)
    # ...
    #
    # I.e. the JSON-LD parsing takes that long
    for data in metadata['microdata']:
        if data['@type'] == 'Person':
            # E.g:
            # {
            #   '@type': 'Person',
            #   '@context': 'http://schema.org',
            #   'additionalType': 'https://dblp.org/rdf/schema#Person',
            #   'url': 'https://dblp.uni-trier.de/pid/65/9656',
            #   'name': 'Ricardo Usbeck'
            # }
            results.append(
                Person(
                    name=data["name"],
                    url=data["url"]
                )
            )

            g.parse(data=json.dumps(data), format='json-ld')

        elif data['@type'] == 'ScholarlyArticle':
            # E.g.
            # {
            #   '@type': 'ScholarlyArticle',
            #   '@context': 'http://schema.org',
            #   'additionalType': 'https://dblp.org/rdf/schema#Publication',
            #   'image': 'https://dblp.uni-trier.de/img/paper-oa.dark.hollow.16x16.png',
            #   'url': 'https://doi.org/10.1109/ACCESS.2022.3173355',
            #   'headline': 'Md. Rashad Al Hasan Rony, ...',
            #   'author':
            #     [
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/251/0778.html',
            #         'name': 'Md. Rashad Al Hasan Rony'
            #       },
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/213/7337.html',
            #         'name': 'Debanjan Chaudhuri'
            #       },
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/65/9656.html',
            #         'name': 'Ricardo Usbeck'
            #       },
            #       {
            #         '@type': 'Person',
            #         'url': 'https://dblp.uni-trier.de/pid/71/4882.html',
            #         'name': 'Jens Lehmann'
            #       }
            #     ],
            #   'name': 'Tree-KGQA: An Unsupervised Approach for Question...',
            #   'isPartOf':
            #     [
            #       {
            #         '@type': 'Periodical',
            #         'name': 'IEEE Access'
            #       },
            #       {
            #         '@type': 'PublicationVolume',
            #         'volumeNumber': '10'
            #       }
            #     ],
            #   'pagination': '50467-50478',
            #   'datePublished': '2022'
            # }
            if type(data["author"]) == list:
                author = ', '.join([authors["name"] for authors in data["author"]])
            else:
                author = data["author"]

            if type(data["url"]) == list:
                url = ', '.join(data["url"])
            else:
                url = data["url"]

            results.append(
                Article(
                    title=data["name"],
                    url=url,
                    authors=author,
                    date=data["datePublished"]
                )
            )

            g.parse(data=json.dumps(data), format='json-ld')
    logger.info(f"Graph g has {len(g)} statements after querying DBLP.")


    return g, results


def zenodo(search_term, g, results):
    response = requests.get('https://zenodo.org/api/records',
                            params={'q': search_term,
                                    'access_token': 'rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL'})

    logger.debug(f'Zenodo response status code: {response.status_code}')
    logger.debug(f'Zenodo response headers: {response.headers}')

    for data in response.json()['hits']['hits']:
        if 'conceptdoi' in data:
            # TODO Align and extend with schema.org concepts
            resource = URIRef(data['conceptrecid'])
            resource_type = URIRef('zenodo:' + data['metadata']['resource_type']['type'])
            g.add((resource, RDF.type, resource_type))
            results.append(
                Zenodo(
                    uri=resource,
                    resource_type=resource_type,
                    url=data["links"]["doi"],
                    date=data['metadata']['publication_date'],
                    title=data['metadata']['title']
                )
            )

    logger.info(f"Graph g has {len(g)} statements after querying Zenodo.")
    return g, results


widget_button = """
        <!DOCTYPE html>
        <html>
           <head>
              <style>
                 .menu-tittle  {font-size: 20px;} 
                 .menu-option  {font-size: 18px;}
                 .menu-suboption {font-size: 15px;}
                 a  { color: blue; }
                 .menu-description { color: gray; display: inline;}
                 .menu-small {width: 20%}
                 .row { display: flex; }
                 .column { flex: 50%;}
              </style>
           </head>
           <body>
              <div class="menu">
                 <h1 class='menu-tittle'>More from NFDI4DS?</h1>
                 <div class="row">
                    <div class="column menu-small">
                       <h2 class='menu-option'><a href='https://www.nfdi4datascience.de/en/events/events'>Events</a></h2>
                    </div>
                    <div class="column menu-small">
                       <h2 class='menu-option'><a href='https://twitter.com/nfdi4ds'>Community</a></h2>
                    </div>
                    <div class="column">
                       <h2 class='menu-option'> Services </h2>
                       <h3 class='menu-suboption'>
                          <a href='https://orkg.org/'>ORKG</a>
                          <p class='menu-description'>The ORKG aims to describe papers in a structured manner.</p>
                       </h3>
                       <h3 class='menu-suboption'>
                          <a href='https://dblp.org/'>DBLP</a>
                            <p class='menu-description'>The dblp computer science bibliography provides 
                                open bibliographic information</p>
                       </h3>
                       <h3 class='menu-suboption'>
                        <a href='https://ceur-ws.org/'>CEUR</a>
                        <p class='menu-description'>CEUR Proceedings is a free open-access publication service</p>
                       </h3>
                       <h3 class='menu-suboption'>
                          <a href='https://mybinder.org/'>MyBinder</a>
                          <p class='menu-description'>Turn a Git repo into a collection of interactive notebooks</p>
                       </h3>
                    </div>
                 </div>
              </div>
           </body>
        </html>
        """

with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            gr.HTML(widget_button)
            input_text = gr.Textbox(label="Search Term")
            search = gr.Button("Search")
            html = gr.HTML("<h1 style = 'font-size: 20px;'>Search Results</h1>")
    search.click(sources, input_text, html)


def open_alex(name, g, results):
    serializable_results = search_openalex.find(name, results)
    search_result = json.dumps(serializable_results)

    g.parse(data=search_result, format='json-ld')
    return g, results


demo.launch()
