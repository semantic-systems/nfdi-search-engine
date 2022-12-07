from flask import Flask, request
import mapping

app = Flask(__name__)

@app.route("/search")
def search_sources():
    keyword = request.args.get('keyword')
    graph, rich_snippet = mapping.sources(keyword)
    return {
        "rich_snippet": rich_snippet,
        "graph": graph
    }
