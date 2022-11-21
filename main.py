import json

import extruct
import gradio as gr
import requests
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import  RDF

class Person:
  def __init__(self, name, URL):
    self.name = name
    self.URL = URL

class Article:
  def __init__(self, title, URL, authors, date):
    self.title = title
    self.URL = URL
    self.authors = authors
    self.date = date

class Zenodo:
  def __init__(self, id, type, URL):
    self.id = id
    self.type = type
    self.URL = URL

def sources(name):
    g = Graph()
    results = []
    g, results = dblp(name, g, results)
    g, results = zenodo(name, g, results)
    # TODO add materialized triples via https://github.com/RDFLib/OWL-RL
    g.parse('zenodo2schema.ttl')
    g = g.serialize(format="turtle")
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
                                h2  {display: inline; font-size: 20px;}
                                h1  {display: inline; font-size: 30px;} 
                                a  { color: blue;  }
                                .faded { color: gray;  }
                                .emoji { font-size:20px }
                                .emoji-title { font-size:30px }
                            </style>
                            </head>
                            <body>"""
    person_result = "<h1>Researchers - </h1><span class='emoji-title'>&#129417;</span><br><br>"
    exist_person = False
    article_result = "<h1>Articles - </h1><span class='emoji-title'>&#128240;</span><br><br>"
    exist_article = False
    zenodo_result = "<h1>Zenodo - </h1><span class='emoji-title'>&#128188;</span><br><br>"
    exist_zenodo = False
    for result in results:
        if type(result) is Person:
            person_result += "<span class='emoji'>&#129417;</span><h2><a href='"+result.URL+"' target='_blank' >"+result.name+\
                                 "</a></h2><p class='faded'>"+result.URL+"</p><br>"
            exist_person = True
        elif type(result) is Article:
            if "," in result.URL:
                article_result += "<p class='faded'>" + result.URL \
                                     + "</p><span class='emoji'>&#128240;</span><h2></i><a href='" +\
                                     result.URL.split(",")[0] + "' target='_blank'>" + \
                                     result.title + "</a></h2> - " + result.date + "<p>" + result.authors + "</p><br>"
            else:
                article_result += "<p class='faded'>" + result.URL +\
                                     "</p><span class='emoji'>&#128240;</span><h2><a href='"+result.URL+\
                                     "' target='_blank'>" + result.title + \
                                     "</a></h2> - "+result.date+"<p>"+result.authors+"</p><br>"
            exist_article = True
        elif type(result) is Zenodo:
            zenodo_result += "<p class='faded'>" + result.URL +\
                                 "</p><span class='emoji'>&#128188;</span><h2><a href='"+\
                                 result.URL+"' target='_blank'>" + result.id \
                                 + "</a></h2><p>" + result.type + "</p><br>"
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
        if('conceptdoi' in data):
            # TODO Align and extend with schema.org concepts
            subject = URIRef(data['conceptdoi'])
            object = URIRef('zenodo:'+data['metadata']['resource_type']['type'])
            g.add((subject, RDF.type, object))
            results.append(Zenodo(subject, object, data["links"]["doi"]))
        if('conceptrecid' in data):
            # TODO parse this
            print('TODO')
    return g, results


with gr.Blocks() as demo:
    gr.HTML(widget_button)
    with gr.Row():
        with gr.Column():
            input_text = gr.Textbox(label="Search Term")
            search = gr.Button("Search")
            html = gr.HTML("<h1 style = 'font-size: 20px;'>Search Results</h1>")
    search.click(sources, input_text, html)

demo.launch()
