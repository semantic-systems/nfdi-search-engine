import logging
import logging.config
import os
import uuid
# from objects import Person, Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Institute, Funder, Publisher, Gesis, Cordis, Orcid, Gepris
from objects import Article, Organization, Person
from flask import Flask, render_template, request, make_response
import threading
from sources import dblp, zenodo, openalex, resodate, wikidata, cordis, gesis, orcid, gepris, ieee #eulg
# import dblp, zenodo, openalex, resodate, wikidata, cordis, gesis, orcid, gepris # , eulg
import details_page


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
def search_results():
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
            'others': []
        }      
        threads = []

        # add all the sources here in this list; for simplicity we should use the exact module name
        # ensure the main method which execute the search is named "search" in the module 
        sources = [resodate]
        # sources = [dblp, zenodo, openalex, resodate, wikidata, cordis, gesis, orcid, gepris]

        for source in sources:
            t = threading.Thread(target=source.search, args=(search_term, results,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
            # print(t.is_alive())
        
        logger.info(f'Got {len(results["publications"])} publications')
        logger.info(f'Got {len(results["researchers"])} researchers')
        logger.info(f'Got {len(results["resources"])} resources')
        logger.info(f'Got {len(results["organizations"])} organizations')
        logger.info(f'Got {len(results["events"])} events')
        logger.info(f'Got {len(results["fundings"])} fundings')
        logger.info(f'Got {len(results["others"])} others')       
        
        return render_template('results.html', results=results, search_term=search_term)


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

@app.route('/publication-details')
def publication_details():
    response = make_response(render_template('publication-details.html'))

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



#region OLD CODE

# @app.route('/index-old')
# def index_new():
#     response = make_response(render_template('index-old.html'))

#     # Set search-session cookie to the session cookie value of the first visit
#     if request.cookies.get('search-session') is None:
#         if request.cookies.get('session') is None:
#             response.set_cookie('search-session', str(uuid.uuid4()))
#         else:
#             response.set_cookie('search-session', request.cookies['session'])

#     return response

# @app.route('/result', methods=['POST', 'GET'])
# def sources():
#     # The search-session cookie setting can still be None if a user enters the
#     # /sources endpoint directly without going to / first!!!
#     logger.debug(
#         f'Search session {request.cookies.get("search-session")} '
#         f'searched for "{request.args.get("txtSearchTerm")}"'
#     )

#     if request.method == 'GET':
#         search_term = request.args.get('txtSearchTerm')

#         results = []
#         threads = []

#         # add all the sources here in this list; for simplicity we should use the exact module name
#         # ensure the main method which execute the search is named "search" in the module 
#         # sources = [dblp, zenodo, openalex, resodate, wikidata, cordis, gesis]
#         sources = [dblp, zenodo, openalex, resodate, wikidata, cordis, gesis, orcid, gepris, ieee] #, eulg]

#         for source in sources:
#             t = threading.Thread(target=source.search, args=(search_term, results,))
#             t.start()
#             threads.append(t)

#         for t in threads:
#             t.join()
#             # print(t.is_alive())

#         data = {
#             'Researchers': [],
#             'Articles': [],
#             'Dataset': [],
#             'Software': [],
#             'Presentation': [],
#             'Poster': [],
#             'Lesson': [],
#             'Video': [],
#             'Institute': [],
#             'Publisher': [],
#             'Funder': [],
#             'Image': [],
#             'Zenodo': [],
#             'Gesis': [],
#             'Cordis': [],
#             'Orcid': [],
#             'Gepris': []
#         }      

#         logger.info(f'Got {len(results)} results')

#         object_mappings = {Person       : 'Researchers'   ,
#                            Article      : 'Articles'      ,
#                            Dataset      : 'Dataset'       ,
#                            Software     : 'Software'      ,
#                            Presentation : 'Presentation'  ,
#                            Poster       : 'Poster'        ,
#                            Lesson       : 'Lesson'        ,
#                            Video        : 'Video'         ,
#                            Institute    : 'Institute'     ,
#                            Publisher    : 'Publisher'     ,
#                            Funder       : 'Funder'        ,
#                            Image        : 'Image'         ,
#                            Zenodo       : 'Zenodo'        ,
#                            Gesis        : 'Gesis'         ,
#                            Cordis       : 'Cordis'        ,
#                            Orcid        : 'Orcid'         ,
#                            Gepris       : 'Gepris'
#                            }

#         for result in results:
#             result_type = type(result)
#             if result_type in object_mappings.keys():
#                 data[object_mappings[result_type]].append(result)
#             else:
#                 logger.warning(f"Type {result_type} of result not yet handled")   
       
        
#         # Remove items without results
#         data = dict((k, result) for k, result in data.items() if result)
#         return render_template('result.html', data=data, search_term=search_term)


#endregion













