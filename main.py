import json

import extruct
import gradio as gr
import requests
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import  RDF


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

def sources(name):
    g = Graph()
    g = dblp(name, g)
    g = zenodo(name, g)
    # TODO add materialized triples via https://github.com/RDFLib/OWL-RL
    g.parse('zenodo2schema.ttl')
    return g.serialize(format="turtle")


def zenodo(name, g):
    response = requests.get('https://zenodo.org/api/records',
                            params={'q': name,
                                    'access_token': 'rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL'})
    for data in response.json()['hits']['hits']:
        if('conceptdoi' in data):
            # TODO Align and extend with schema.org concepts
            subject = URIRef(data['conceptdoi'])
            object = URIRef('zenodo:'+data['metadata']['resource_type']['type'])
            g.add((subject, RDF.type, object))
        if('conceptrecid' in data):
            # TODO parse this
            print('TODO')
    return g

def dblp(name, g):
    headers = {'Accept': 'application/json'}

    response = requests.get('https://dblp.uni-trier.de/search?q=' + name, headers=headers)
    print(response.status_code)
    # TODO unclear why here are only a few but now all results returned
    metadata = extract_metadata(response.content)

    # TODO unclear why this loop takes so long
    for data in metadata['microdata']:
        if data['@type'] == 'Person':
            g.parse(data=json.dumps(data), format='json-ld')
        if data['@type'] == 'ScholarlyArticle':
            g.parse(data=json.dumps(data), format='json-ld')

    print(f"Graph g has {len(g)} statements.")

    return g


demo = gr.Interface(fn=sources, inputs="text", outputs="text")

demo.launch()
