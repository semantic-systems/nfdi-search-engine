import logging
from objects import Person, Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Institute, Funder, Publisher, Gesis, Cordis
from flask import Flask, render_template, request
import threading
import dblp, zenodo, openalex, resodate, wikidata, cordis, gesis
import details_page

logger = logging.getLogger('nfdi_search_engine')
app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/sources', methods=['POST', 'GET'])
def sources():
    if request.method == 'GET':
        search_term = request.args.get('txtSearchTerm')

        results = []
        threads = []

        # add all the sources here in this list; for simplicity we should use the exact module name
        # ensure the main method which execute the search is named "search" in the module 
        # sources = [dblp, zenodo, openalex, resodate, wikidata, cordis, gesis]
        sources = [dblp, zenodo, openalex, resodate, wikidata, cordis]
        for source in sources:
            t = threading.Thread(target=source.search, args=(search_term, results,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
            # print(t.is_alive())

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

        logger.info(f'Got {len(results)} results')

        object_mappings = {Person       : 'Researchers'   ,
                           Article      : 'Articles'      ,
                           Dataset      : 'Dataset'       ,
                           Software     : 'Software'      ,
                           Presentation : 'Presentation'  ,
                           Poster       : 'Poster'        ,
                           Lesson       : 'Lesson'        ,
                           Video        : 'Video'         ,
                           Institute    : 'Institute'     ,
                           Publisher    : 'Publisher'     ,
                           Funder       : 'Funder'        ,
                           Image        : 'Image'         ,
                           Zenodo       : 'Zenodo'        ,
                           Gesis        : 'Gesis'         ,
                           Cordis       : 'Cordis'        ,                
                           }

        for result in results:
            result_type = type(result)
            if result_type in object_mappings.keys():
                data[object_mappings[result_type]].append(result)
            else:
                logger.warning(f"Type {result_type} of result not yet handled")   
       
        
        # Remove items without results
        data = dict((k, result) for k, result in data.items() if result)
        return render_template('result.html', data=data, search_term=search_term)


@app.route('/details', methods=['POST', 'GET'])
def details():
    if request.method == 'GET':
        details = {}
        links = {}
        name = ''
        search_term = request.args.get('searchTerm')
        if search_term.startswith('https://orcid.org/'):
            details, links, name = details_page.search_by_orcid(search_term)
            return render_template('details.html', search_term=search_term, details=details, links=links, name=name)

        orcid = details_page.get_orcid(search_term)
        if orcid != '':
            return render_template('details.html', search_term=orcid, details=details, links=links, name='')

        if search_term.startswith('https://openalex.org/'):
            details, links, name = details_page.search_openalex(search_term)
        elif search_term.startswith('https://dblp'):
            details, links, name = details_page.search_dblp(search_term)

        return render_template('details.html', search_term=search_term, details=details, links=links, name=name)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)
