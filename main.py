import json

import extruct
import gradio as gr
import requests
from rdflib import Graph, URIRef, Literal, BNode, Namespace
from rdflib.namespace import RDF, FOAF, DCTERMS, XSD, SDO
from objects import Person, Zenodo, Article
from search_openalex import *

def sources(name):
    g = Graph()
    results = []
    g, results = dblp(name, g, results)
    g, results = zenodo(name, g, results)
    g, results  = open_alex(name, g, results)
    # TODO add materialized triples via https://github.com/RDFLib/OWL-RL
    g.parse('zenodo2schema.ttl')
    g = g.serialize(format="ttl")
    return format_results(results)


def format_results(results):
    """From the results obtained from the databases it creates an HTML, and it returns it

        Args:
            results: array of the different types of results

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
    person_result = "<h1 class='title'>Researchers - </h1><span class='emoji-title'>&#129417;</span><br><br>"
    exist_person = False
    article_result = "<h1 class='title'>Articles - </h1><span class='emoji-title'>&#128240;</span><br><br>"
    exist_article = False
    zenodo_result = "<h1 class='title'>Zenodo - </h1><span class='emoji-title'>&#128188;</span><br><br>"
    exist_zenodo = False
    for result in results:
        if type(result) is Person:
            person_result += "<span class='emoji'>&#129417;</span><h2 class='subtitle'><a href='"+result.URL+"' target='_blank' >"+result.name + \
                                 "</a></h2><p class='faded'>"+result.URL+"</p><br>"
            exist_person = True
        elif type(result) is Article:
            if "," in result.URL:
                article_result += "<p class='url'>" + result.URL \
                                     + "</p><span class='emoji'>&#128240;</span><h2 class='subtitle'></i><a href='" +\
                                     result.URL.split(",")[0] + "' target='_blank'>" + \
                                     result.title + "</a></h2> - " + result.date + "<p>" + result.authors + "</p><br>"
            else:
                article_result += "<p class='url'>" + result.URL +\
                                     "</p><span class='emoji'>&#128240;</span><h2 class='subtitle'><a href='"+result.URL+\
                                     "' target='_blank'>" + result.title + \
                                     "</a></h2> - "+result.date+"<p>"+result.authors+"</p><br>"
            exist_article = True
        elif type(result) is Zenodo:
            zenodo_result += "<p class='url'>" + result.URL +\
                                 "</p><span class='emoji'>&#128188;</span><h2 class='subtitle'><a href='"+\
                                 result.URL+"' target='_blank'>" + result.title + \
                                 "</a></h2> - "+result.date+ "<p>" + result.type + "</p><br>"
            exist_zenodo = True
        else:
            print("Type of result not yet handled")

    #Checking that we have actual results and act accordingly if not
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
def extract_metadata(text):
    """Extract all metadata present in the page and return a dictionary of metadata lists.

    Args:

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



def dblp(name, g, results):
    headers = {'Accept': 'application/json'}

    response = requests.get('https://dblp.uni-trier.de/search?q=' + name, headers=headers)
    print(response.status_code)
    # TODO unclear why here are only a few but now all results returned
    metadata = extract_metadata(response.content)

    # TODO unclear why this loop takes so long
    for data in metadata['microdata']:
        if data['@type'] == 'Person':
            results.append(Person(data["name"], data["url"]))
            g.parse(data=json.dumps(data), format='json-ld')
        if data['@type'] == 'ScholarlyArticle':
            author = ""
            if type(data["author"]) == list:
                author = ','.join([authors["name"] for authors in data["author"]])
            else:
                author = data["author"]

            url = ""
            if type(data["url"]) == list:
                url = ','.join(data["url"])
            else:
                url = data["url"]

            results.append(Article(data["name"], url, author, data["datePublished"]))
            g.parse(data=json.dumps(data), format='json-ld')

    print(f"Graph g has {len(g)} statements.")

    return g, results


def zenodo(name, g, results):
    response = requests.get('https://zenodo.org/api/records',
                            params={'q': name,
                                    'access_token': 'rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL'})
    for data in response.json()['hits']['hits']:
        if 'conceptdoi' in data:
            # TODO Align and extend with schema.org concepts
            subject = URIRef(data['conceptrecid'])
            object = URIRef('zenodo:' + data['metadata']['resource_type']['type'])
            g.add((subject, RDF.type, object))
            results.append(Zenodo(subject, object, data["links"]["doi"], data['metadata']['publication_date'], data['metadata']['title']))
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
            input_text = gr.Textbox(label="Search Term", lines=1, max_lines=1)
            search = gr.Button("Search")
            html = gr.HTML("<h1 style = 'font-size: 20px;'>Search Results</h1>")
    input_text.submit(sources, input_text, html)
    search.click(sources, input_text, html)

def open_alex(name, g, results):
    serializable_results, results = find(name, results)
    search_result = json.dumps(serializable_results)
    g.parse(data=search_result, format='json-ld')
    return g, results


demo.launch()
