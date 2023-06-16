import logging
import logging.config
import os
import uuid

from objects import Person, Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Institute, Funder, Publisher, Gesis, Cordis
from flask import Flask, render_template, request, make_response
import threading
import search_dblp
import search_zenodo
import search_openalex
import resodate
import details_page
import search_wikidata
import search_gesis
import search_cordis

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


@app.route('/sources', methods=['POST', 'GET'])
def sources():
    # The search-session cookie setting can still be None if a user enters the
    # /sources endpoint directly without going to / first!!!
    logger.debug(
        f'Search session {request.cookies.get("search-session")} '
        f'searched for "{request.args.get("txtSearchTerm")}"'
    )

    if request.method == 'GET':
        search_term = request.args.get('txtSearchTerm')
        results = []
        data = {
            'Researchers': [],
            'Articles': [],
            'Dataset': [],
            'Software': [],
            'Presentation': [],
            'Poster': [],
            'Lesson': [],
            'Video': [],
            'Institute': [],
            'Publisher': [],
            'Funder': [],
            'Image': [],
            'Zenodo': [],
            'Gesis': [],
            'Cordis': [],
        }
        results = []
        threads = []

        # Define a function for each API call
        def dblp_search():
            search_dblp.dblp(search_term, results)
        
        def zenodo_search():
            search_zenodo.zenodo(search_term, results)
        
        def openalex_search():
            search_openalex.find(search_term, results)

        def resodate_search():
            resodate.search(search_term, results)

        def wikidata_search():
            search_wikidata.wikidata_search(search_term, results)

        def gesis_search():
            search_gesis.gesis(search_term, results)

        def cordis_search():
            search_cordis.cordis(search_term, results)
        
        # Create a thread for each API call
        t1 = threading.Thread(target=dblp_search)
        t2 = threading.Thread(target=zenodo_search)
        t3 = threading.Thread(target=openalex_search)
        t4 = threading.Thread(target=wikidata_search)
        t5 = threading.Thread(target=resodate_search)
        t6 = threading.Thread(target=gesis_search)
        t7 = threading.Thread(target=cordis_search)

        # Start all threads
        t1.start()
        t2.start()
        t3.start()
        t4.start()
        t5.start()
        t6.start()
        t7.start()

        # Wait for all threads to finish
        t1.join()
        t2.join()
        t3.join()
        t4.join()
        t5.join()
        t6.join()
        t7.join()

        logger.info(f'Got {len(results)} results')
        for result in results:
            if isinstance(result, Person):
                data['Researchers'].append(result)

            elif isinstance(result, Article):
                data['Articles'].append(result)

            elif isinstance(result, Dataset):
                data['Dataset'].append(result)

            elif isinstance(result, Software):
                data['Software'].append(result)

            elif isinstance(result, Presentation):
                data['Presentation'].append(result)

            elif isinstance(result, Poster):
                data['Poster'].append(result)

            elif isinstance(result, Lesson):
                data['Lesson'].append(result)

            elif isinstance(result, Video):
                data['Video'].append(result)

            elif isinstance(result, Institute):
                data['Institute'].append(result)

            elif isinstance(result, Publisher):
                data['Publisher'].append(result)

            elif isinstance(result, Funder):
                data['Funder'].append(result)

            elif isinstance(result, Image):
                data['Image'].append(result)

            elif isinstance(result, Zenodo):
                data['Zenodo'].append(result)

            elif isinstance(result, Gesis):
                data['Gesis'].append(result)

            elif isinstance(result, Cordis):
                data['Cordis'].append(result)   
            else:
                logger.warning(f"Type {type(result)} of result not yet handled")
        # Remove items without results
        data = dict((k, result) for k, result in data.items() if result)
        return render_template('result.html', data=data, search_term=search_term)


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
        return render_template('details.html', search_term=search_term, details=details, links=links, name=name)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)
