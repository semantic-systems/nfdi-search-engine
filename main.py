import logging
from objects import Person, Zenodo, Article, Ieee
from flask import Flask, render_template, request
import threading
import search_dblp
import search_zenodo
import search_openalex
import search_ieee

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
        data = {
            'Researchers': [],
            'Articles': [],
            'Zenodo': [],
            'Ieee': [],
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

        def ieee_search():
            search_ieee.ieee(search_term, results)
        
        # Create a thread for each API call
        t1 = threading.Thread(target=dblp_search)
        t2 = threading.Thread(target=zenodo_search)
        t3 = threading.Thread(target=openalex_search)
        t4 = threading.Thread(target=ieee_search)

        # Start all threads
        t1.start()
        t2.start()
        t3.start()
        t4.start()

        # Wait for all threads to finish
        t1.join()
        t2.join()
        t3.join()
        t4.join()
        logger.info(f'Got {len(results)} results')
        for result in results:
            if isinstance(result, Person):
                data['Researchers'].append(result)

            elif isinstance(result, Article):
                data['Articles'].append(result)

            elif isinstance(result, Zenodo):
                data['Zenodo'].append(result)

            elif isinstance(result, Ieee):
                data['Ieee'].append(result)
                
            else:
                logger.warning(f"Type {type(result)} of result not yet handled")
        return render_template('result.html', data=data, search_term=search_term)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)
