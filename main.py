import logging
import gradio as gr
import os
from objects import Person, Zenodo, Article
import search_dblp
import search_zenodo
import search_openalex

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')


def sources(search_term):
    results = []
    search_dblp.dblp(search_term, results)
    search_zenodo.zenodo(search_term, results)
    search_openalex.find(search_term, results)
    # results = [dblp_search_results, openalex_search_results, zenodo_search_results]
    logger.info(f'Got {len(results)} results')
    return format_results(results)


def format_results(results):
    """From the results obtained from the databases it creates an HTML page, and it returns it

        Args:
            results: List of the different results

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

    person_result = "<h1 class='title'>Researchers - </h1>" \
                    "<span class='emoji-title'>&#129417;</span>" \
                    "<br><br>"
    exist_person = False

    article_result = "<h1 class='title'>Articles - </h1>" \
                     "<span class='emoji-title'>&#128240;</span>" \
                     "<br><br>"
    exist_article = False

    zenodo_result = "<h1 class='title'>Zenodo - </h1>" \
                    "<span class='emoji-title'>&#128188;</span>" \
                    "<br><br>"
    exist_zenodo = False

    for result in results:
        if isinstance(result, Person):
            person_result += \
                f"<h2 class='subtitle'><a href='{result.url}' target='_blank' >{result.name}</a></h2>" \
                f"<p class='faded'>{result.url}</p><br>"
            exist_person = True
            # TA: Since the url is used as an anchor link with the author name, no need to repeat it.
            # Or resolve the author names that come from DBLP and OA, then list the links.

        elif isinstance(result, Article):
            if "," in result.url:
                url = result.url.split(',')[0]
            else:
                url = result.url

            article_result +=\
                f"<p class='url'>{url}</p>" \
                f"<h2 class='subtitle'><a href='{url}' target='_blank'>{result.title}</a></h2>" \
                f" - {result.date}" \
                f"<p>{result.authors}</p>" \
                f"<br>"
            exist_article = True

        elif isinstance(result, Zenodo):
            zenodo_result +=\
                f"<p class='url'>{result.url}</p>" \
                f"<h2 class='subtitle'><a href='{result.url}' target='_blank'>{result.title}</a></h2>" \
                f" - {result.date}" \
                f"<p>{result.resource_type}</p>" \
                f"<br>"
            exist_zenodo = True
        else:
            logger.warning(f"Type {type(result)} of result not yet handled")

    # Checking that we have actual results and act accordingly if not
    if not exist_person:
        person_result = ""
    if not exist_article:
        article_result = ""
    if not exist_zenodo:
        zenodo_result = ""
    if not exist_zenodo and not exist_article and not exist_person:
        person_result = "<br><br><h1>No results found </h1><span class='emoji-title'>&#128549;</span>"

    return formatted_results + person_result + article_result + zenodo_result + "</body></html>"

widget_button = """
        <!DOCTYPE html>
        <html>
           <head>
              <style>
                 .menu-tittle  {font-size: 20px;} 
                 .menu-option  {font-size: 18px;}
                 .menu-suboption {font-size: 15px;}
                 a  { color: blue; }
                 .menu-description { color: gray; display: inline;}
                 .menu-small {width: 20%}
                 .row { display: flex; }
                 .column { flex: 50%;}
              </style>
           </head>
           <body>
              <div class="menu">
                 <h1 class='menu-tittle'>More from NFDI4DS?</h1>
                 <div class="row">
                    <div class="column menu-small">
                       <h2 class='menu-option'><a href='https://www.nfdi4datascience.de/en/events/events'>Events</a></h2>
                    </div>
                    <div class="column menu-small">
                       <h2 class='menu-option'><a href='https://twitter.com/nfdi4ds'>Community</a></h2>
                    </div>
                    <div class="column">
                       <h2 class='menu-option'> Services </h2>
                       <h3 class='menu-suboption'>
                          <a href='https://orkg.org/'>ORKG</a>
                          <p class='menu-description'>The ORKG aims to describe papers in a structured manner.</p>
                       </h3>
                       <h3 class='menu-suboption'>
                          <a href='https://dblp.org/'>DBLP</a>
                            <p class='menu-description'>The dblp computer science bibliography provides 
                                open bibliographic information</p>
                       </h3>
                       <h3 class='menu-suboption'>
                        <a href='https://ceur-ws.org/'>CEUR</a>
                        <p class='menu-description'>CEUR Proceedings is a free open-access publication service</p>
                       </h3>
                       <h3 class='menu-suboption'>
                          <a href='https://mybinder.org/'>MyBinder</a>
                          <p class='menu-description'>Turn a Git repo into a collection of interactive notebooks</p>
                       </h3>
                    </div>
                 </div>
              </div>
           </body>
        </html>
        """

with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            gr.HTML(widget_button)
            input_text = gr.Textbox(label="Search Term", lines=1, max_lines=1)
            search = gr.Button("Search")
            html = gr.HTML("<h1 style = 'font-size: 20px;'>Search Results</h1>")
    input_text.submit(sources, input_text, html) # from https://github.com/semantic-systems/nfdi-search-engine/pull/42/commits/051dd31f3a3bf61c9ea5ebdb8570cd77e7f7f12a
    search.click(sources, input_text, html)


demo.launch(server_name="0.0.0.0", share=True)
