import logging
import logging.config
import os
import uuid
# from objects import Person, Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Institute, Funder, Publisher, Gesis, Cordis, Orcid, Gepris
from objects import Article, Organization, Person, Dataset, Project
from flask import Flask, render_template, request, make_response
import threading
from sources import dblp_publications, openalex_publications, zenodo, wikidata_publications
from sources import resodate, oersi, ieee, eudat, openaire_products
from sources import cordis, gesis, orcid, gepris, eulg, re3data, orkg

import details_page
from sources.gepris import org_details
import utils
import deduplicator

logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')
app = Flask(__name__)


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
        # sources = [resodate, oersi, openalex, orcid, dblp, zenodo, gesis, ieee, cordis, gepris, eudat, wikidata, openaire, eulg]
        sources = [dblp_publications, openalex_publications, zenodo, wikidata_publications, resodate, oersi, ieee,
                   eudat, openaire_products, re3data, orkg]
        # sources = [zenodo]
        for source in sources:
            t = threading.Thread(target=source.search, args=(search_term, results,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
            # print(t.is_alive())

        # deduplicator.convert_publications_to_csv(results["publications"])
        results["publications"] = deduplicator.perform_entity_resolution_publications(results["publications"])

        # sort all the results in each category
        results["publications"] = utils.sort_results_publications(results["publications"])        

        # on the first page load, only push top 20 records in each category
        top_records_count = 20
        total_results = {} # the dict to keep the total number of search results 
        for k, v in results.items():
            logger.info(f'Got {len(v)} {k}')
            total_results[k] = len(v)
            results[k] = v[:top_records_count]

        results["timedout_sources"] = list(set(results["timedout_sources"]))
        logger.info('Following sources got timed out:' + ','.join(results["timedout_sources"]))       
        
        template_response = render_template('results.html', results=results, search_term=search_term)    
        logger.info('search server call completed - after render call')

        return template_response


@app.route('/chatbox')
def chatbox():
    response = make_response(render_template('chatbox.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/publication-details/<string:doi>', methods=['POST', 'GET'])
@utils.timeit
def publication_details(doi):
    doi = request.args.get('doi', '').replace('-.-', '/')
    print(doi)

    response = make_response(render_template('publication-details.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

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
