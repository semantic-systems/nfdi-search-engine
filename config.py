import os
from dotenv import find_dotenv, load_dotenv

from typing import Optional, Dict, Any
from pydantic import Field, HttpUrl, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# load environment variables
_ = load_dotenv(find_dotenv())

class Settings(BaseSettings):
    """Helper for loading and validating .env values"""

    PREFERRED_URL_SCHEME: str = "http"
    SECRET_KEY: Optional[str] = None
    
    # API Keys
    IEEE_API_KEY: Optional[str] = None
    OPENCITATIONS_API_KEY: Optional[str] = None
    CORE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # OAuth
    CLIENT_ID_GOOGLE: Optional[str] = None
    CLIENT_SECRET_GOOGLE: Optional[str] = None
    CLIENT_ID_GITHUB: Optional[str] = None
    CLIENT_SECRET_GITHUB: Optional[str] = None
    CLIENT_ID_ORCID: Optional[str] = None
    CLIENT_SECRET_ORCID: Optional[str] = None
    REDIRECT_URI_ORCID: Optional[str] = None

    # Dashboard auth
    DASHBOARD_USERNAME: str
    DASHBOARD_PASSWORD: str

    # LLAMA
    LLAMA3_USERNAME: Optional[str] = None
    LLAMA3_PASSWORD: Optional[str] = None

    # Elasticsearch + Chatbot
    ELASTIC_SERVER: str = Field(default="https://dev.nfdi-elastic.nliwod.org/")
    ELASTIC_USERNAME: str = Field(default="elastic")
    ELASTIC_PASSWORD: Optional[str] = None
    CHATBOT_SERVER: str = Field(default="https://nfdi-chatbot.nliwod.org")

    model_config = SettingsConfigDict(env_file=find_dotenv(), env_file_encoding='utf-8', extra='ignore')

def validate_env():
    """
    Try to create a Settings object and return it. If .env values are missing/incorrect,
    prints a warning and returns a Settings object in which all missing/incorrect values
    are None.
    """
    try:
        settings = Settings()
        return settings
    except ValidationError as e:
        print("\n--- ERROR: Missing or Invalid Environment Variables ---")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error['loc'])
            print(f"Variable: {loc}, Error: {error['msg']}")
        print("-------------------------------------------------------\n")

        # create an unsafe settings object
        # warning: missing keys are set to None!
        all_fields = Settings.model_fields.keys()
        safe_data = {field: os.environ.get(field) for field in all_fields}

        return Settings.model_construct(**safe_data)

app_settings = validate_env()

class Config:

    # copy over all the values from the settings
    if app_settings:
        PREFERRED_URL_SCHEME = app_settings.PREFERRED_URL_SCHEME
        SECRET_KEY = app_settings.SECRET_KEY

        IEEE_API_KEY = app_settings.IEEE_API_KEY
        OPENCITATIONS_API_KEY = app_settings.OPENCITATIONS_API_KEY
        CORE_API_KEY = app_settings.CORE_API_KEY
        OPENAI_API_KEY = app_settings.OPENAI_API_KEY

        CLIENT_ID_GOOGLE = app_settings.CLIENT_ID_GOOGLE
        CLIENT_SECRET_GOOGLE = app_settings.CLIENT_SECRET_GOOGLE
        CLIENT_ID_GITHUB = app_settings.CLIENT_ID_GITHUB
        CLIENT_SECRET_GITHUB = app_settings.CLIENT_SECRET_GITHUB
        CLIENT_ID_ORCID = app_settings.CLIENT_ID_ORCID
        CLIENT_SECRET_ORCID = app_settings.CLIENT_SECRET_ORCID
        REDIRECT_URI_ORCID = app_settings.REDIRECT_URI_ORCID

        LLAMA3_USERNAME = app_settings.LLAMA3_USERNAME
        LLAMA3_PASSWORD = app_settings.LLAMA3_PASSWORD

        DASHBOARD_USERNAME = app_settings.DASHBOARD_USERNAME
        DASHBOARD_PASSWORD = app_settings.DASHBOARD_PASSWORD

        ELASTIC_SERVER = app_settings.ELASTIC_SERVER
        ELASTIC_USERNAME = app_settings.ELASTIC_USERNAME
        ELASTIC_PASSWORD = app_settings.ELASTIC_PASSWORD
        CHATBOT_SERVER = app_settings.CHATBOT_SERVER

    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"

    REQUEST_HEADER_USER_AGENT = "nfdi4dsBot/1.0 (https://www.nfdi4datascience.de/nfdi4dsBot/; nfdi4dsBot@nfdi4datascience.de)"
    REQUEST_TIMEOUT = 5

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
            "search-endpoint": f"https://zenodo.org/api/records?size=25&q=",
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
            "get-resource-endpoint": f"https://huggingface.co/api/models/",
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
            "get-resource-endpoint": f"https://huggingface.co/api/datasets/",
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
            "get-researcher-endpoint": "https://pub.orcid.org/v3.0/",
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
        "DataCite": {
            "logo": {
                "name": "DataCite",
                "link": "https://datacite.org/",
                "src": "DataCite-Logo.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "datacite",
            "search-endpoint": "https://api.datacite.org/dois?query=titles.title:",
            "get-publication-endpoint": "https://api.datacite.org/dois/"
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
        "OpenCitations": {
            "logo": {
                "name": "OpenCitations",
                "link": "https://opencitations.net/",
                "src": "opencitations.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "opencitations",
            "citations-endpoint": "https://opencitations.net/index/api/v2/citations/doi:",
            "get-publication-references-endpoint": "https://opencitations.net/index/api/v2/references/doi:",
            "metadata-endpoint": "https://opencitations.net/meta/api/v1/metadata/doi:",
        },
        "CORE": {
            "logo": {
                "name": "CORE",
                "link": "https://core.ac.uk/",
                "src": "core.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "core",
            "search-endpoint": f"https://api.core.ac.uk/v3/search/works/?limit={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
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
        "resodate": {
            "logo": {
                "name": "resodate",
                "link": "https://resodate.org/",
                "src": "resodate-logo.png",
                "width": "w-100",
                "height": "h-100",
                },
            "module": "resodate",
            "search-endpoint": f"https://resodate.org/api/search/resource_metadata/_search?pretty&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        },
        # "OERSI": {
        #     "module": "oersi",
        #     "search-endpoint": f"https://oersi.org/resources/api/search/oer_data/_search?pretty&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&q=",
        # },
        "IEEE": {
            "logo": {
                "name": "IEEE",
                "link": "https://ieeexplore.ieee.org/",
                "src": "ieee.gif",
                "width": "w-100",
                "height": "h-70",
            },
            "module": "ieee",
            "search-endpoint": f"https://ieeexploreapi.ieee.org/api/v1/search/articles?max_records={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&querytext=",
            "get-publication-endpoint": f"https://ieeexploreapi.ieee.org/api/v1/search/articles?doi=",
            "api-key-param": "apikey",
        },
        # "EUDAT": {
        #     "module": "eudat",
        #     "search-endpoint": f"https://b2share.eudat.eu/api/records/?page=1&size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&sort=bestmatch&q=",
        #     "record-base-url": f"https://b2share.eudat.eu/records/",
        # },
        # "CORDIS": {
        #     "module": "cordis",
        #     "search-endpoint": f"https://cordis.europa.eu/search?p=1&num={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&srt=Relevance:decreasing&format=json&q=contenttype='project'%20AND%20",
        # },
        "ORKG": {
            "logo": {
                "name": "ORKG",
                "link": "https://orkg.org/",
                "src": "orkg.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "orkg",
            "search-endpoint": f"https://orkg.org/api/resources/?size={NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT}&base_class=Paper&q=",
        },
        "gepris": {
            "logo": {
                "name": "GEPRIS",
                "link": "https://gepris.dfg.de/",
                "src": "GEPRIS_Logo.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "gepris",
            "search-endpoint": f"https://gepris.dfg.de/gepris/OCTOPUS?context=projekt&hitsPerPage=1&index=0&language=en&task=doSearchSimple&keywords_criterion=",
        },
        "CODALAB": {
            "logo": {
                "name": "CODALAB",
                "link": "https://worksheets.codalab.org/",
                "src": "codalab-logo.png",
                "width": "w-100",
                "height": "h-100",
            },
            "module": "codalab",
            "search-endpoint": "https://worksheets.codalab.org/rest/bundles?include_display_metadata=1&include=owner&.limit="
                            + str(NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT)
                            + "&keywords=",
            "get-resource-endpoint": "https://worksheets.codalab.org/rest/bundles/",
        },
    }

    LLMS = {
        "openai": {
            "url_chat_completions": "https://api.openai.com/v1/chat/completions",
            "url_images_generations": "https://api.openai.com/v1/images/generations",
            "open_api_key": app_settings.OPENAI_API_KEY
        },
        "llama3": {
            "url": "https://llm-chat.skynet.coypu.org/generate_text",
            "username": app_settings.LLAMA3_USERNAME,
            "password": app_settings.LLAMA3_PASSWORD
        },
    }

    CHATBOT = {
        "chatbot_enable": False,
        "chatbot_server": app_settings.CHATBOT_SERVER,
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

    ELASTIC = {
        "server": app_settings.ELASTIC_SERVER,
        "username": app_settings.ELASTIC_USERNAME,
        "password": app_settings.ELASTIC_PASSWORD
    }

    OAUTH2_PROVIDERS = {
        # Google OAuth 2.0 documentation:
        # https://developers.google.com/identity/protocols/oauth2/web-server#httprest
        "google": {
            "client_id": app_settings.CLIENT_ID_GOOGLE,
            "client_secret": app_settings.CLIENT_SECRET_GOOGLE,
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
            "client_id": app_settings.CLIENT_ID_GITHUB,
            "client_secret": app_settings.CLIENT_SECRET_GITHUB,
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
        #     'client_id': app_settings.CLIENT_ID_ORCID,
        #     'client_secret': app_settingsCLIENT_SECRET_ORCID,
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

    