import requests
from rdflib import URIRef
from rdflib.namespace import RDF
from objects import Zenodo

# rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL access token zenodo
def search(name, g, results):
    response = requests.get('https://zenodo.org/api/records',
                            params={'q': name,
                                    'access_token': 'rtldW8mT6PgLkj6fUL46nu02YQaUGYfGT8FjuoJMTK4gdwizDLyt6foRVaGL'})
    for data in response.json()['hits']['hits']:
        if 'conceptdoi' in data:
            # TODO Align and extend with schema.org concepts
            subject = URIRef(data['conceptrecid'])
            object = URIRef('zenodo:' + data['metadata']['resource_type']['type'])
            g.add((subject, RDF.type, object))
            results.append(Zenodo(subject, object, data["links"]["doi"], data['metadata']['publication_date'],
                                  data['metadata']['title']))

    response.close()

    return g, results
