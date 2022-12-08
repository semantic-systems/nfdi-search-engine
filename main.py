import gradio as gr
import controller

# Simple text menu temporarily replacing the NFDI widget menu.
# The intended menu is at https://tibhannover.gitlab.io/nfdi4ds/nfdi4ds-widget/ but Gradio is not compatible with it
widget_menu = """
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

# Formation of GUI through blocks to create a vertical view
with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            gr.HTML(widget_menu)
            input_text = gr.Textbox(label="Search Term")
            search = gr.Button("Search")
            html = gr.HTML("<h1 style = 'font-size: 20px;'>Search Results</h1>")
    search.click(controller.search_sources, input_text, html)

demo.launch()
