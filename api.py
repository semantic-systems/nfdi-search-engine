from flask import Flask, request
import merger

app = Flask(__name__)


@app.route("/search")
def search_sources():
    """
    Handles the search expecting keyword in the URL params.

    Returns: rich snippet and graph as JSON

    """
    keyword = request.args.get('keyword')
    graph, rich_snippet = merger.sources(keyword)
    return {
        "rich_snippet": rich_snippet,
        "graph": graph
    }
