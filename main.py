import logging
import logging.config
import os
import uuid
# from objects import Person, Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Institute, Funder, Publisher, Gesis, Cordis, Orcid, Gepris
from objects import Article, Organization, Person, Dataset, Project
from flask import Flask, render_template, request, make_response, session
from flask_session import Session
import threading
from sources import dblp_publications, openalex_publications, zenodo, wikidata_publications, wikidata_researchers
from sources import resodate, oersi, ieee, eudat, openaire_products
from sources import dblp_researchers
from sources import crossref, semanticscholar
from sources import cordis, gesis, orcid, gepris, eulg, re3data, orkg

from chatbot import chatbot

import details_page
from sources.gepris import org_details
import utils
import deduplicator
import copy
import requests
import uuid
import json

logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')
app = Flask(__name__)
app.secret_key = 'NfD14D$G@t3w@Y'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route('/')
def index():
    response = make_response(render_template('index.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/results', methods=['POST', 'GET'])
@utils.timeit
def search_results():

    logger.info('search server call initiated.')
    # The search-session cookie setting can still be None if a user enters the
    # /sources endpoint directly without going to / first!!!
    logger.debug(
        f'Search session {request.cookies.get("search-session")} '
        f'searched for "{request.args.get("txtSearchTerm")}"'
    )

    if request.method == 'GET':
        search_term = request.args.get('txtSearchTerm')
        session['search-term'] = search_term

        results = {
            'publications': [],
            'researchers': [],
            'resources': [],
            'organizations': [],
            'events': [],
            'fundings': [],
            'others': [],
            'timedout_sources': []
        }
        threads = []

        # add all the sources here in this list; for simplicity we should use the exact module name
        # ensure the main method which execute the search is named "search" in the module         
        sources = [dblp_publications, openalex_publications, zenodo, wikidata_publications, resodate, oersi, ieee,
                   eudat, openaire_products, dblp_researchers, re3data, orkg]
        # sources = [openalex_publications]
        for source in sources:
            t = threading.Thread(target=source.search, args=(search_term, results,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
            # print(t.is_alive())

        # deduplicator.convert_publications_to_csv(results["publications"])
        # results["publications"] = deduplicator.perform_entity_resolution_publications(results["publications"])

        # sort all the results in each category
        results["publications"] = utils.sort_search_results(search_term, results["publications"])  
        results["researchers"] = utils.sort_search_results(search_term, results["researchers"])             
        
        #store the search results in the session
        session['search-results'] = copy.deepcopy(results)

        
        # Chatbot - push search results to chatbot server for embeddings generation
        if utils.config['chatbot_feature_enable'] == "True":

            # Convert a UUID to a 32-character hexadecimal string
            search_uuid = uuid.uuid4().hex
            session['search_uuid'] = search_uuid
            
            def send_search_results_to_chatbot(search_uuid: str):
                print('request is about to start')
                chatbot_server = utils.config['chatbot_server'] 
                save_docs_with_embeddings = utils.config['endpoint_save_docs_with_embeddings'] 
                request_url = f'{chatbot_server}{save_docs_with_embeddings}/{search_uuid}'        
                response = requests.post(request_url, json=json.dumps(results, default=vars))
                response.raise_for_status() 
                print('request completed')

            # create a new daemon thread
            chatbot_thread = threading.Thread(target=send_search_results_to_chatbot, args=(search_uuid,), daemon=True)
            # start the new thread
            chatbot_thread.start()
            # sleep(1)
        

        # on the first page load, only push top 20 records in each category
        number_of_records_to_show_on_page_load = int(utils.config["number_of_records_to_show_on_page_load"])        
        total_results = {} # the dict to keep the total number of search results 
        displayed_results = {} # the dict to keep the total number of search results currently displayed to the user
        
        for k, v in results.items():
            logger.info(f'Got {len(v)} {k}')
            total_results[k] = len(v)
            results[k] = v[:number_of_records_to_show_on_page_load]
            displayed_results[k] = len(results[k])

        results["timedout_sources"] = list(set(results["timedout_sources"]))
        logger.info('Following sources got timed out:' + ','.join(results["timedout_sources"]))  

        session['total_search_results'] = total_results
        session['displayed_search_results'] = displayed_results 
        
        template_response = render_template('results.html', results=results, total_results=total_results, search_term=search_term)    
        logger.info('search server call completed - after render call')

        return template_response

@app.route('/load-more-publications', methods=['GET'])
def load_more_publications():
    print('load more publications')

    #define a new results dict for publications to take new publications from the search results stored in the session
    results = {}
    results['publications'] = session['search-results']['publications']

    total_search_results_publications = session['total_search_results']['publications']
    displayed_search_results_publications = session['displayed_search_results']['publications']
    number_of_records_to_append_on_lazy_load = int(utils.config["number_of_records_to_append_on_lazy_load"])       
    results['publications'] = results['publications'][displayed_search_results_publications:displayed_search_results_publications+number_of_records_to_append_on_lazy_load]
    session['displayed_search_results']['publications'] = displayed_search_results_publications+number_of_records_to_append_on_lazy_load
    return render_template('components/publications.html', results=results)  

@app.route('/load-more-researchers', methods=['GET'])
def load_more_researchers():
    print('load more researchers')

    #define a new results dict for researchers to take new researchers from the search results stored in the session
    results = {}
    results['researchers'] = session['search-results']['researchers']

    total_search_results_researchers = session['total_search_results']['researchers']
    displayed_search_results_researchers = session['displayed_search_results']['researchers']
    number_of_records_to_append_on_lazy_load = int(utils.config["number_of_records_to_append_on_lazy_load"])       
    results['researchers'] = results['researchers'][displayed_search_results_researchers:displayed_search_results_researchers+number_of_records_to_append_on_lazy_load]
    session['displayed_search_results']['researchers'] = displayed_search_results_researchers+number_of_records_to_append_on_lazy_load
    return render_template('components/researchers.html', results=results)     

@app.route('/are-embeddings-generated', methods=['GET'])
def are_embeddings_generated():

    #Check the embeddings readiness only if the chatbot feature is enabled otherwise return False
    if utils.config['chatbot_feature_enable'] == "True":
        print('are_embeddings_generated')
        uuid = session['search_uuid']
        chatbot_server = utils.config['chatbot_server'] 
        are_embeddings_generated = utils.config['endpoint_are_embeddings_generated'] 
        request_url = f"{chatbot_server}{are_embeddings_generated}/{uuid}"    
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", request_url, headers=headers)    
        json_response = response.json()
        print('json_response:', json_response)
        return str(json_response['file_exists'])
    else:
        return str(True)

@app.route('/get-chatbot-answer', methods=['GET'])
def get_chatbot_answer():
    print('get chatbot answer')

    question = request.args.get('question')
    print('User asked:', question)

    # context = session['search-results']
    # answer = chatbot.getAnswer(question=question, context=context)

    search_uuid = session['search_uuid']
    answer = chatbot.getAnswer(question=question, search_uuid=search_uuid)
    
    return answer


# @app.route('/chatbot')
# def chatbot():
#     response = make_response(render_template('chatbot.html'))

#     # Set search-session cookie to the session cookie value of the first visit
#     if request.cookies.get('search-session') is None:
#         if request.cookies.get('session') is None:
#             response.set_cookie('search-session', str(uuid.uuid4()))
#         else:
#             response.set_cookie('search-session', request.cookies['session'])

#     return response


from jinja2.filters import FILTERS
import json
def format_digital_obj_url(value):
    sources_list = []
    for source in value.source:
        source_dict = {}
        source_dict['doi'] = value.identifier
        source_dict['sname'] = source.name
        source_dict['sid'] = value.identifier
        sources_list.append(source_dict)
    return json.dumps(sources_list)
FILTERS["format_digital_obj_url"] = format_digital_obj_url

def format_authors_for_citations(value):
    authors = ""
    for author in value:
        authors += (author.name + " and ")    
    return authors.rstrip(' and ') + "."
FILTERS["format_authors_for_citations"] = format_authors_for_citations

from urllib.parse import unquote
import ast

@app.route('/publication-details/<path:sources>', methods=['GET'])
@utils.timeit
def publication_details(sources):

    sources = unquote(sources)
    sources = ast.literal_eval(sources)    
    for source in sources:
        doi = source['doi']
    
    publication = openalex_publications.get_publication(doi="https://doi.org/"+doi)
    response = make_response(render_template('publication-details.html', publication=publication))

    print("response:", response)
    return response

@app.route('/publication-details-references/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_references(doi):
    print("doi:", doi)    
    
    publication = crossref.get_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/references.html', publication=publication))

    print("response:", response)
    return response

@app.route('/publication-details-recommendations/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_recommendations(doi):
    print("DOI:", doi)    
    publications = semanticscholar.get_recommendations_for_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/recommendations.html', publications=publications))
    print("response:", response)
    return response

@app.route('/publication-details-citations/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_citations(doi):
    print("DOI:", doi)    
    publications = semanticscholar.get_citations_for_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/citations.html', publications=publications))
    print("response:", response)
    return response

@app.route('/resource-details')
def resource_details():
    response = make_response(render_template('resource-details.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/researcher-details')
def researcher_details():
    response = make_response(render_template('researcher-details.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/organization-details/<string:organization_id>/<string:organization_name>', methods=['GET'])
def organization_details(organization_id, organization_name):
    try:

        # Create a response object
        """ response = make_response()

        # Set search-session cookie to the session cookie value of the first visit
        if request.cookies.get('search-session') is None:
            if request.cookies.get('session') is None:
                response.set_cookie('search-session', str(uuid.uuid4()))
            else:
                response.set_cookie('search-session', request.cookies['session'])"""

        # Call the org_details function from the gepris module to fetch organization details by id
        organization, sub_organization, sub_project = org_details(organization_id, organization_name)

        if organization or sub_organization or sub_project:
            # Render the organization-details.html template
            return render_template('organization-details.html', organization=organization,
                                   sub_organization=sub_organization, sub_project=sub_project)
        else:
            # Handle the case where organization details are not found (e.g., return a 404 page)
            return render_template('error.html', error_message='Organization details not found.')

    except ValueError as ve:
        return render_template('error.html', error_message=str(ve))
    except Exception as e:
        return render_template('error.html', error_message='An error occurred: ' + str(e))


@app.route('/events-details')
def events_details():
    response = make_response(render_template('events-details.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/fundings-details')
def fundings_details():
    response = make_response(render_template('fundings-details.html'))
    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/details', methods=['POST', 'GET'])
def details():
    if request.method == 'GET':
        # data_type = request.args.get('type')
        details = {}
        links = {}
        name = ''
        search_term = request.args.get('searchTerm')
        if search_term.startswith('https://openalex.org/'):
            details, links, name = details_page.search_openalex(search_term)
        elif search_term.startswith('https://dblp'):
            details, links, name = details_page.search_dblp(search_term)
        elif search_term.startswith('http://www.wikidata.org'):
            details, links, name = details_page.search_wikidata(search_term)
        elif search_term.startswith('https://orcid.org/'):
            details, links, name = details_page.search_orcid(search_term)
        return render_template('details.html', search_term=search_term, details=details, links=links, name=name)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)
