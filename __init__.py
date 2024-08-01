# import os
# import logging
# import logging.config
# from flask import Flask
# from flask_login import LoginManager
# from flask_session import Session
# from config import Config

# logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
# logger = logging.getLogger('nfdi_search_engine')
# app = Flask(__name__)
# app.config.from_object(Config)
# Session(app)

# login = LoginManager(app)
# login.login_view = 'login'

# from models import models