from rdflib import Graph
from objects import Person, Zenodo, Article
import search_openalex
import zenodo
import dblp


def sources(name):
    """
    It queries all the databases merging the results into single objects
        Initially authored by Ricardo Usbeck
    Args:
        name: keyword to search for in the databases

    Returns:
        the graph object and the formatted results

    """
    g = Graph()
    results = []
    g, results = dblp.search(name, g, results)
    g, results = zenodo.search(name, g, results)
    g, results = search_openalex.open_alex(name, g, results)
    # TODO add materialized triples via https://github.com/RDFLib/OWL-RL
    g.parse('zenodo2schema.ttl')
    g = g.serialize(format="ttl")
    return g, format_results(results)


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
