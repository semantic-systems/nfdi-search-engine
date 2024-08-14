import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"

    REQUEST_HEADER_USER_AGENT = "nfdi4dsBot/1.0 (https://www.nfdi4datascience.de/nfdi4dsBot/; nfdi4dsBot@nfdi4datascience.de)"
    REQUEST_TIMEOUT = 5

    NUMBER_OF_RECORDS_TO_SHOW_ON_PAGE_LOAD = 20
    NUMBER_OF_RECORDS_TO_APPEND_ON_LAZY_LOAD = 10

    DATA_SOURCES = {
        "dblp - Publications": {
            "module": "dblp_publications", 
            "endpoint": "https://dblp.org/search/publ/api?format=json&h=25&q=",
        }, 
        # "dblp - Researchers": {
        #     "module": "dblp_researchers", 
        #     "endpoint": "https://dblp.org/search/author/api?format=json&h=25&q=",
        # },
        # "openalex - Publications": {
        #     "module": "openalex_publications", 
        #     "endpoint": "https://api.openalex.org/works?page=1&per-page=25&search=",
        # },
        # "openalex - Researchers": {
        #     "module": "openalex_researchers", 
        #     "endpoint": "https://api.openalex.org/authors?page=1&per-page=25&search=",
        # },
        # "zenodo": {
        #     "module": "zenodo", 
        #     "endpoint": "https://zenodo.org/api/records?size=25&q=",
        # },
        # "wikidata - Publications": {
        #     "module": "wikidata_publications", 
        #     "endpoint": "https://query.wikidata.org/sparql?format=json&query=",
        # },
        # "wikidata - Researchers": {
        #     "module": "wikidata_researchers", 
        #     "endpoint": "https://query.wikidata.org/sparql?format=json&query=",
        # },
        # "resodate": {
        #     "module": "resodate", 
        #     "endpoint": "https://resodate.org/resources/api/search/oer_data/_search?pretty&size=25&q=",
        # },
        # "oersi": {
        #     "module": "oersi", 
        #     "endpoint": "https://oersi.org/resources/api/search/oer_data/_search?pretty&size=25&q=",
        # },
        # "ieee": {
        #     "module": "ieee", 
        #     "endpoint": "http://ieeexploreapi.ieee.org/api/v1/search/articles?apikey={api_key}&max_records=25&querytext=",
        # },
        # "eudat": {
        #     "module": "eudat", 
        #     "endpoint": "https://b2share.eudat.eu/api/records/?page=1&size=25&sort=bestmatch&q=",
        # },
        # "openaire - Products": {
        #     "module": "openaire_products", 
        #     "endpoint": "https://api.openaire.eu/search/researchProducts?format=json&size=25&keywords=",
        # },
    }

    OAUTH2_PROVIDERS = {
        # Google OAuth 2.0 documentation:
        # https://developers.google.com/identity/protocols/oauth2/web-server#httprest
        'google': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
            'authorize_url': 'https://accounts.google.com/o/oauth2/auth',
            'token_url': 'https://accounts.google.com/o/oauth2/token',
            'userinfo': {
                'url': 'https://www.googleapis.com/oauth2/v3/userinfo',
                'email': lambda json: json['email'],
            },
            'scopes': ['https://www.googleapis.com/auth/userinfo.email'],
        },

        # GitHub OAuth 2.0 documentation:
        # https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
        'github': {
            'client_id': os.environ.get('GITHUB_CLIENT_ID'),
            'client_secret': os.environ.get('GITHUB_CLIENT_SECRET'),
            'authorize_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'userinfo': {
                'url': 'https://api.github.com/user/emails',
                'email': lambda json: json[0]['email'],
            },
            'scopes': ['user:email'],
        },

        # ORCID OAuth 2.0 documentation:
        # https://info.orcid.org/documentation/api-tutorials/api-tutorial-get-and-authenticated-orcid-id/        
        'orcid': {
            'client_id': os.environ.get('ORCID_CLIENT_ID'),
            'client_secret': os.environ.get('ORCID_CLIENT_SECRET'),
            'authorize_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'userinfo': {
                'url': 'https://api.github.com/user/emails',
                'email': lambda json: json[0]['email'],
            },
            'scopes': ['user:email'],
        },
    }