import os

# load environment variables
from dotenv import find_dotenv, load_dotenv

_ = load_dotenv(find_dotenv())


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    IEEE_API_KEY = os.environ.get("IEEE_API_KEY", "")

    REQUEST_HEADER_USER_AGENT = "nfdi4dsBot/1.0 (https://www.nfdi4datascience.de/nfdi4dsBot/; nfdi4dsBot@nfdi4datascience.de)"
    REQUEST_TIMEOUT = 100

    NUMBER_OF_RECORDS_TO_SHOW_ON_PAGE_LOAD = 20
    NUMBER_OF_RECORDS_TO_APPEND_ON_LAZY_LOAD = 10
    NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT = 100

    DATE_FORMAT_FOR_REPORT = "%B %d, %Y"
    DATE_FORMAT_FOR_ELASTIC = "%Y-%m-%d"

    DATA_SOURCES = {
        "GESIS KG": {
            "logo": {
                "name": "GESIS",
                "link": "https://www.gesis.org/",
                "src": "gesis.svg",
                "width": "w-100",
                "height": "h-70",
            },
            "module": "gesis_kg_publication",
            "search-endpoint": f"https://data.gesis.org/gesiskg/sparql?default-graph-uri=&query=",
        },
        "GESIS KG - Dataset": {
            "logo": {
                "name": "GESIS",
                "link": "https://www.gesis.org/",
                "src": "gesis.svg",
                "width": "w-100",
                "height": "h-70",
            },
            "module": "gesis_kg_dataset",
            "search-endpoint": f"https://data.gesis.org/gesiskg/sparql?default-graph-uri=&query=",
        },
        "OPENALEX - Publications": {
            "logo": {
                "name": "OPENALEX",
                "link": "https://openalex.org/",
                "src": "openalex.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "openalex_publications",
            "search-endpoint": f"https://api.openalex.org/works?page=1&per-page={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&search=",
            "get-publication-endpoint": "https://api.openalex.org/works/",
            "get-researcher-publications-endpoint": "https://api.openalex.org/works?filter=author.id:",
        },
        "OPENALEX - Researchers": {
            "logo": {
                "name": "OPENALEX",
                "link": "https://openalex.org/",
                "src": "openalex.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "openalex_researchers",
            "search-endpoint": f"https://api.openalex.org/authors?page=1&per-page={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&search=",
            "get-researcher-endpoint": "https://api.openalex.org/authors/",
            "get-researcher-publications-endpoint": "https://api.openalex.org/works?filter=author.id:",
        },
        "ZENODO": {
            "logo": {
                "name": "ZENODO",
                "link": "https://zenodo.org/",
                "src": "zenodo.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "zenodo",
            "search-endpoint": f"https://zenodo.org/api/records?size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
            "get-publication-endpoint": f"https://zenodo.org/api/records/",
        },
        "WIKIDATA - Publications": {
            "logo": {
                "name": "WIKIDATA",
                "link": "https://www.wikidata.org/",
                "src": "wikidata.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "wikidata_publications",
            "search-endpoint": f"https://query.wikidata.org/sparql?format=json&query=",
        },
        "WIKIDATA - Researchers": {
            "logo": {
                "name": "WIKIDATA",
                "link": "https://www.wikidata.org/",
                "src": "wikidata.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "wikidata_researchers",
            "search-endpoint": f"https://query.wikidata.org/sparql?format=json&query=",
        },
        "Huggingface - Models": {
            "logo": {
                "name": "HUGGING FACE",
                "link": "https://huggingface.co/",
                "src": "huggingface.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "huggingface_models",
            "search-endpoint": f"https://huggingface.co/api/models?limit={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&search=",
        },
        "Huggingface - Datasets": {
            "logo": {
                "name": "HUGGING FACE",
                "link": "https://huggingface.co/",
                "src": "huggingface.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "huggingface_datasets",
            "search-endpoint": f"https://huggingface.co/api/datasets?limit={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&search=",
        },
        "OPENAIRE - Products": {
            "logo": {
                "name": "OPENAIRE",
                "link": "https://www.openaire.eu/",
                "src": "openaire.webp",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "openaire_products",
            "search-endpoint": f"https://api.openaire.eu/search/researchProducts?format=json&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&keywords=",
            "get-publication-endpoint": f"https://api.openaire.eu/search/researchProducts?format=json&doi=",
        },
        "OPENAIRE - Projects": {
            "logo": {
                "name": "OPENAIRE",
                "link": "https://www.openaire.eu/",
                "src": "openaire.webp",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "openaire_projects",
            "search-endpoint": f"https://api.openaire.eu/search/projects?format=json&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&keywords=",
        },
        "ORCID": {
            "logo": {
                "name": "ORCID",
                "link": "https://orcid.org/",
                "src": "orcid.svg",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "orcid",
            "search-endpoint": f"https://pub.orcid.org/v3.0/expanded-search/?start=0&rows={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        },
        "CROSSREF - Publications": {
            "logo": {
                "name": "CROSSREF",
                "link": "https://www.crossref.org/",
                "src": "crossref.svg",
                "width": "w-100",
                "height": "h-60",
            },
            "module": "crossref_publications",
            "search-endpoint": f"https://api.crossref.org/works?rows={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&query=",
            "get-publication-endpoint": "https://api.crossref.org/works/",
            "get-publication-references-endpoint": "https://api.crossref.org/works/",
        },
        "SEMANTIC SCHOLAR - Publications": {
            "logo": {
                "name": "SEMANTIC SCHOLAR",
                "link": "https://www.semanticscholar.org/",
                "src": "semanticscholar.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "semanticscholar_publications",
            # "search-endpoint": f"",
            # "get-publication-endpoint": "https://api.semanticscholar.org/graph/v1/paper/",
            "citations-endpoint": f"https://api.semanticscholar.org/graph/v1/paper/",
            "recommendations-endpoint": f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/",
        },
        "SEMANTIC SCHOLAR - Researchers": {
            "logo": {
                "name": "SEMANTIC SCHOLAR",
                "link": "https://www.semanticscholar.org/",
                "src": "semanticscholar.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "semanticscholar_researchers",
            # "search-endpoint": f"",
            # "get-researcher-endpoint": f"https://api.semanticscholar.org/graph/v1/author/",
        },
        "RE3DATA": {
            "logo": {
                "name": "RE3DATA",
                "link": "https://www.re3data.org/",
                "src": "re3data.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "re3data",
            "search-endpoint": f"https://www.re3data.org/api/beta/repositories?query=",
            "get-resource-endpoint": f"https://www.re3data.org/api/v1/repository/",
        },
        "DBLP - VENUES": {
            "logo": {
                "name": "DBLP",
                "link": "https://dblp.org/",
                "src": "dblp.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "dblp_venues",
            "search-endpoint": f"https://dblp.org/search/venue/api?format=json&h={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        },
        # "dblp - Publications": {
        #     "module": "dblp_publications",
        #     "search-endpoint": f"https://dblp.org/search/publ/api?format=json&h={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        # },
        # #######Though DBLP has an endpoint for researchers but their details are minimal hence should not be harvested.
        # "dblp-Researchers": {
        #    "module": "dblp_researchers",
        #    "search-endpoint": f"https://dblp.org/search/author/api?format=json&h={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        # },
        # "resodate": {
        #     "module": "resodate",
        #     "search-endpoint": f"https://resodate.org/resources/api/search/oer_data/_search?pretty&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        # },
        # "OERSI": {
        #     "module": "oersi",
        #     "search-endpoint": f"https://oersi.org/resources/api/search/oer_data/_search?pretty&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        # },
        # "IEEE": { #IEEE API key is not working, therefore this has been disabled for now.
        #     "logo": {
        #         "src": "ieee.gif",
        #         "width": "w-100",
        #         "height": "h-70",
        #     },
        #     "module": "ieee",
        #     "search-endpoint": f"http://ieeexploreapi.ieee.org/api/v1/search/articles?apikey={IEEE_API_KEY}&max_records={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&querytext=",
        #     "get-publication-endpoint": f"http://ieeexploreapi.ieee.org/api/v1/search/articles?apikey={IEEE_API_KEY}&doi=",
        # },
        # "EUDAT": {
        #     "module": "eudat",
        #     "search-endpoint": f"https://b2share.eudat.eu/api/records/?page=1&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&sort=bestmatch&q=",
        #     "record-base-url": f"https://b2share.eudat.eu/records/",
        # },
        # "CORDIS": {
        #     "module": "cordis",
        #     "search-endpoint": f"https://cordis.europa.eu/search?p=1&num={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&srt=Relevance:decreasing&format=json&q=contenttype='project'%20AND%20",
        # },
        # "ORKG": {
        #     "module": "orkg",
        #     "search-endpoint": f"https://orkg.org/api/resources/?size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        # },
        # "gepris": {
        #     "module": "gepris",
        #     "search-endpoint": f"https://gepris.dfg.de/gepris/OCTOPUS?context=projekt&hitsPerPage=1&index=0&language=en&task=doSearchSimple&keywords_criterion=",
        # },
    }

    LLMS = {
        "openai": {
            "url_chat_completions": "https://api.openai.com/v1/chat/completions",
            "url_images_generations": "https://api.openai.com/v1/images/generations",
            "open_api_key": os.environ.get("OPENAI_API_KEY", ""),
        },
        "llama3": {
            "url": "https://llm-chat.skynet.coypu.org/generate_text",
            "username": os.environ.get("LLAMA3_USERNAME", ""),
            "password": os.environ.get("LLAMA3_PASSWORD", ""),
        },
    }

    CHATBOT = {
        "chatbot_enable": True,
        "chatbot_server": os.environ.get("CHATBOT_SERVER", ""),
        "endpoint_chat": "/chat",
        "endpoint_save_docs_with_embeddings": "/save-docs-with-embeddings",
        "endpoint_are_embeddings_generated": "/are-embeddings-generated",
        # open ai ... these two parameters should be passed onto chatbot
        "openai_model_version": "gpt-3.5-turbo-0125",
        "openai_temperature": 2,
    }

    ENTITY_RESOLUTION = {
        "settings_file_publications": "static/weights/publications-settings.json",
    }

    # MAPPING_PREFERENCE is used to map the fields from the platform responses to the objects in objects.py
    # i.e. abstracts from publications are first taken from OPENALEX - Publications, then from CROSSREF - Publications, etc.
    MAPPING_PREFERENCE = {
        "researchers": {
            "__default__": ["OPENALEX - Researchers", "ORCID"],
            "identifier": ["ORCID", "OPENALEX - Researchers"],
        },
        "publications": {
            "__default__": [
                "CROSSREF - Publications",
                "OPENALEX - Publications",
                "OPENAIRE - Products",
            ],
            "abstract": [
                "OPENALEX - Publications",
                "CROSSREF - Publications",
                "OPENAIRE - Products",
            ],
            "reference": ["CROSSREF - Publications"],
            "citation": ["CROSSREF - Publications"],
        },
    }

    # ELASTIC = {
    #     "server": os.environ.get('ELASTIC_SERVER',""),
    #     "username": os.environ.get('ELASTIC_USERNAME',""),
    #     "password": os.environ.get('ELASTIC_PASSWORD',""),
    # }

    OAUTH2_PROVIDERS = {
        # Google OAuth 2.0 documentation:
        # https://developers.google.com/identity/protocols/oauth2/web-server#httprest
        "google": {
            "client_id": os.environ.get("CLIENT_ID_GOOGLE"),
            "client_secret": os.environ.get("CLIENT_SECRET_GOOGLE"),
            "authorize_url": "https://accounts.google.com/o/oauth2/auth",
            "token_url": "https://accounts.google.com/o/oauth2/token",
            "userinfo": {
                "url": "https://www.googleapis.com/oauth2/v3/userinfo",
                "email": lambda json: json["email"],
            },
            "scopes": ["https://www.googleapis.com/auth/userinfo.email"],
        },
        # GitHub OAuth 2.0 documentation:
        # https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
        "github": {
            "client_id": os.environ.get("CLIENT_ID_GITHUB"),
            "client_secret": os.environ.get("CLIENT_SECRET_GITHUB"),
            "authorize_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo": {
                "url": "https://api.github.com/user/emails",
                "email": lambda json: json[0]["email"],
            },
            "scopes": ["user:email"],
        },
        # # ORCID OAuth 2.0 documentation:
        # # https://info.orcid.org/documentation/api-tutorials/api-tutorial-get-and-authenticated-orcid-id/
        # 'orcid': {
        #     'client_id': os.environ.get('CLIENT_ID_ORCID'),
        #     'client_secret': os.environ.get('CLIENT_SECRET_ORCID'),
        #     'authorize_url': 'https://sandbox.orcid.org/oauth/authorize',
        #     'token_url': 'https://sandbox.orcid.org/oauth/token',
        #     'userinfo': {
        #         'url': '',
        #         'email': lambda json: json[0]['email'],
        #     },
        #     'scopes': ['/read-limited'],
        # },
    }

    ERROR_MESSAGES = {
        400: "Error 400: Bad Request.",
        401: "Error 401: Unauthorized.",
        403: "Error 403: Forbidden.",
        404: "Error 404: Page not found.",
        405: "Error 405: Method Not Allowed.",
        422: "Error 422: Unprocessable Entity.",
        500: "Error 500: Internal Server Error.",
        502: "Error 502: Bad Gateway.",
        503: "Error 503: Service Unavailable.",
    }
