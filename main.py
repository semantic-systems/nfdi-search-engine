
import os
import uuid
import threading
import copy
import requests
import json
import logging
import logging.config
import secrets
from urllib.parse import urlsplit, urlencode
import importlib

from flask import Flask, render_template, request, make_response, session, jsonify, redirect, flash, url_for, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_session import Session

from config import Config
# from sources import crossref_publications, semanticscholar
from chatbot import chatbot

from sources.gepris import org_details
import utils
import deduplicator
import gen_ai

logging.config.fileConfig(os.getenv('LOGGING_FILE_CONFIG', './logging.conf'))
logger = logging.getLogger('nfdi_search_engine')
app = Flask(__name__)
app.config.from_object(Config)
Session(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

#region MODELS

from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from dataclasses import dataclass, fields, field
from flask_login import UserMixin
# ...
@dataclass
class User(UserMixin):
    id: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    password_hash: str = ""
    oauth_source: str = "self"
    included_data_sources: str = ""
    excluded_data_sources: str = ""

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def __repr__(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(id):
    user = User()
    user.id = id
    user = utils.get_user_by_id(user)
    return user

#endregion


#region FORMS

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, widgets
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, StopValidation
from wtforms.fields import SelectMultipleField


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    # def validate_username(self, username):
    #     user = db.session.scalar(sa.select(User).where(
    #         User.username == username.data))
    #     if user is not None:
    #         raise ValidationError('Please use a different username.')

    # def validate_email(self, email):
    #     user = db.session.scalar(sa.select(User).where(
    #         User.email == email.data))
    #     if user is not None:
    #         raise ValidationError('Please use a different email address.')

class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', render_kw={'disabled':'disabled'},)
    submit = SubmitField('Save')

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(html_tag='ol', prefix_label=False)
    option_widget = widgets.CheckboxInput()

class MultiCheckboxAtLeastOne():
    def __init__(self, message=None):
        if not message:
            message = 'At least one option must be selected.'
        self.message = message

    def __call__(self, form, field):
        if len(field.data) == 0:
            raise StopValidation(self.message)

class PreferencesForm(FlaskForm):
    data_sources = MultiCheckboxField('Data Sources', validators=[MultiCheckboxAtLeastOne()], coerce=str)
    submit = SubmitField("Save")


#endregion


#region JINJA2 FILTERS
from jinja2.filters import FILTERS
import json
def format_digital_obj_url(value, identifier_type):
    return f"{identifier_type}:{value.identifier}"
    # sources_list = []
    # for source in value.source:
    #     source_dict = {}
    #     source_dict['doi'] = value.identifier
    #     source_dict['sname'] = source.name
    #     source_dict['sid'] = source.identifier
    #     sources_list.append(source_dict)
    # return json.dumps(sources_list)
    
FILTERS["format_digital_obj_url"] = format_digital_obj_url

def format_authors_for_citations(value):
    authors = ""
    for author in value:
        authors += (author.name + " and ")    
    return authors.rstrip(' and ') + "."
FILTERS["format_authors_for_citations"] = format_authors_for_citations

import re
def regex_replace(s, find, replace):
    """A non-optimal implementation of a regex filter"""
    return re.sub(find, replace, s)
FILTERS["regex_replace"] = regex_replace

#endregion

#region ROUTES

@app.route("/ping")
def ping():
    if (app.config["SECRET_KEY"] == ""):
        return make_response(render_template('error.html',error_message='Environment variables are not set. Kindly set all the required variables.'))
    
    return jsonify(ping="NFDI4DS Gateway is up and running :) ")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        session["current-user-email"] = current_user.email
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User()
        user.email = form.email.data
        res_flag, user = utils.get_user_by_email(user)        
        if not res_flag or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        session["current-user-email"] = user.email
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.set_password(form.password.data)
        utils.add_user(user)
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# authization code copied from https://github.com/miguelgrinberg/flask-oauth-example
@app.route('/authorize/<provider>')
def oauth2_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))

    provider_data = app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)

    # generate a random string for the state parameter
    session['oauth2_state'] = secrets.token_urlsafe(16)

    # create a query string with all the OAuth2 parameters
    qs = urlencode({
        'client_id': provider_data['client_id'],
        'redirect_uri': url_for('oauth2_callback', provider=provider,
                                _external=True),
        'response_type': 'code',
        'scope': ' '.join(provider_data['scopes']),
        'state': session['oauth2_state'],
    })

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data['authorize_url'] + '?' + qs)

@app.route('/callback/<provider>')
def oauth2_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))

    provider_data = app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)

    # if there was an authentication error, flash the error messages and exit
    if 'error' in request.args:
        for k, v in request.args.items():
            if k.startswith('error'):
                flash(f'{k}: {v}')
        return redirect(url_for('index'))

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args['state'] != session.get('oauth2_state'):
        abort(401)

    # make sure that the authorization code is present
    if 'code' not in request.args:
        abort(401)

    # exchange the authorization code for an access token
    response = requests.post(provider_data['token_url'], data={
        'client_id': provider_data['client_id'],
        'client_secret': provider_data['client_secret'],
        'code': request.args['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': url_for('oauth2_callback', provider=provider,
                                _external=True),
    }, headers={'Accept': 'application/json'})
    if response.status_code != 200:
        abort(401)
    oauth2_token = response.json().get('access_token')
    if not oauth2_token:
        abort(401)

    # use the access token to get the user's email address
    response = requests.get(provider_data['userinfo']['url'], headers={
        'Authorization': 'Bearer ' + oauth2_token,
        'Accept': 'application/json',
    })
    if response.status_code != 200:
        abort(401)
    email = provider_data['userinfo']['email'](response.json())

    # find or create the user in the database
    user = User()
    user.email = email    
    #extract the local part of the email and derive the name from it
    full_name = email.split('@')[0]
    full_name_with_spaces = full_name.replace('-', ' ').replace('.', ' ').replace('_', ' ')
    full_name_tokens = full_name_with_spaces.split(' ')
    if len(full_name_tokens) > 1:
        user.first_name = full_name_tokens[0]
        user.last_name = full_name_tokens[1]
    else:
        user.first_name = full_name    
    response_flag, user = utils.get_user_by_email(user)    
    if response_flag: # user (email) already exists         
        if provider != user.oauth_source:
            user.oauth_source = provider
            utils.update_user(user)
    else:
        utils.add_user(user)  
        
    # log the user in
    login_user(user)
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        # current_user.email = form.email.data
        utils.update_user(current_user)
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    return render_template('profile.html', title='Profile',
                           form=form)

@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():

    form = PreferencesForm()
    # populate the forms dynamically with the values in the configuration and database
    data_sources_list = app.config['DATA_SOURCES']
    form.data_sources.choices = [(source, source) for source in app.config['DATA_SOURCES'].keys()]
    # if it's a post request and we validated successfully
    if request.method == 'POST' and form.validate_on_submit():
        # get our choices again, could technically cache these in a list if we wanted but w/e
        all_sources = app.config['DATA_SOURCES'].keys()
        # need a list to hold the selections
        included_data_sources = []
        excluded_data_sources = []
        # looping through the choices, we check the choice ID against what was passed in the form
        for source in all_sources:
            # when we find a match, we then append the Choice object to our list
            if source in form.data_sources.data:
                included_data_sources.append(source)
            else:
                excluded_data_sources.append(source)
        # now all we have to do is update the users choices records
        current_user.included_data_sources = '; '.join(included_data_sources)
        current_user.excluded_data_sources = '; '.join(excluded_data_sources)
        utils.update_user_preferences_data_sources(current_user)
        flash('Your preferences have been saved.', 'success')
    else:
        # tell the form what's already selected
        form.data_sources.data = [source for source in current_user.included_data_sources.split('; ')]
    return render_template('preferences.html', title='Preferences', form=form)

@app.route('/')
@utils.set_cookies
def index():  
    response = make_response(render_template('index.html'))  
    return response

@app.route('/update-visitor-id', methods=['GET'])
@utils.timeit
def update_visitor_id():
    visitor_id = request.args.get('visitor_id')
    print(f"{visitor_id=}")    
    utils.update_visitor_id(visitor_id)
    return str(True)


@app.route('/results', methods=['POST', 'GET'])
@utils.timeit
@utils.set_cookies
def search_results():
    
    search_term = request.args.get('txtSearchTerm', '')
    utils.log_activity(f"loading search results for {search_term}")  
    utils.log_search_term(search_term) 

    results = {
        'publications': [],
        'researchers': [],
        'resources': [],
        'organizations': [],
        'events': [],
        'projects': [],
        'others': [],
        'timedout_sources': [] ### this should be removed. no longer used
    }

    failed_sources = []

    if request.method == 'GET':
        # search_term = request.args.get('txtSearchTerm')
        session['search-term'] = search_term

        for k in results.keys(): results[k] = []
        threads = []

        #Load all the sources from config.py used to harvest data related to search term 
        sources = []
        if current_user.is_anonymous:
            for module in app.config['DATA_SOURCES']:
                if app.config['DATA_SOURCES'][module].get('search-endpoint','').strip() != "":
                    sources.append(module)
        else:
            excluded_data_sources = current_user.excluded_data_sources.split('; ')
            for module in app.config['DATA_SOURCES']:
                if app.config['DATA_SOURCES'][module].get('search-endpoint','').strip() != "" and module not in excluded_data_sources:
                    sources.append(module)

        for source in sources:
            module_name = app.config['DATA_SOURCES'][source].get('module', '')            
            t = threading.Thread(target=(importlib.import_module(f'sources.{module_name}')).search, args=(source, search_term, results, failed_sources,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
            # print(t.is_alive())

        if len(failed_sources) > 0:
            flash(f"Following sources could not be harvested: { ', '.join(failed_sources)}", category='error')

        # deduplicator.convert_publications_to_csv(results["publications"])
        # results["publications"] = deduplicator.perform_entity_resolution_publications(results["publications"])

        # sort all the results in each category
        threads = [] 
        for k in results.keys():           
            t = threading.Thread(target=utils.sort_search_results, args=(search_term, results[k],))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # results["publications"] = utils.sort_search_results(search_term, results["publications"])  
        # results["researchers"] = utils.sort_search_results(search_term, results["researchers"])  
        # results["resources"] = utils.sort_search_results(search_term, results["resources"]) 
        # results["organizations"] = utils.sort_search_results(search_term, results["organizations"]) 
        # results["events"] = utils.sort_search_results(search_term, results["events"]) 
        # results["projects"] = utils.sort_search_results(search_term, results["projects"]) 
        # results["others"] = utils.sort_search_results(search_term, results["others"])             
        
        #store the search results in the session
        session['search-results'] = copy.deepcopy(results)        

        # Chatbot - push search results to chatbot server for embeddings generation
        if (app.config['CHATBOT']['chatbot_enable']):

            # Convert a UUID to a 32-character hexadecimal string
            search_uuid = uuid.uuid4().hex
            session['search_uuid'] = search_uuid
            
            def send_search_results_to_chatbot(search_uuid: str):
                print('request is about to start')
                chatbot_server = app.config['CHATBOT']['chatbot_server'] 
                save_docs_with_embeddings = app.config['CHATBOT']['endpoint_save_docs_with_embeddings'] 
                request_url = f'{chatbot_server}{save_docs_with_embeddings}/{search_uuid}'        
                response = requests.post(request_url, json=json.dumps(results, default=vars))
                response.raise_for_status() 
                print('request completed')

            # create a new daemon thread
            chatbot_thread = threading.Thread(target=send_search_results_to_chatbot, args=(search_uuid,), daemon=True)
            # start the new thread
            chatbot_thread.start()
            # sleep(1)
        

        # on the first page load, only push top XX records in each category
        number_of_records_to_show_on_page_load = int(app.config["NUMBER_OF_RECORDS_TO_SHOW_ON_PAGE_LOAD"])        
        total_results = {} # the dict to keep the all the search results 
        displayed_results = {} # the dict to keep the search results currently displayed to the user
        
        for k, v in results.items():
            logger.info(f'Got {len(v)} {k}')
            total_results[k] = len(v)
            results[k] = v[:number_of_records_to_show_on_page_load]
            displayed_results[k] = len(results[k])          

        session['total_search_results'] = total_results
        session['displayed_search_results'] = displayed_results 
        
        template_response = render_template('results.html', results=results, total_results=total_results, search_term=search_term)    
        logger.info('search server call completed - after render call')

        return template_response

@app.route('/update_search_result/<string:source>/<string:source_identifier>/<path:doi>', methods=['GET'])
def update_search_result(source: str, source_identifier: str, doi):
    module_name = app.config['DATA_SOURCES'][source].get('module', '')            
    resource = importlib.import_module(f'sources.{module_name}').get_resource(source, source_identifier, doi.replace("DOI:",""))
    return render_template(f'partials/search-results/resource-block.html', resource=resource)

@app.route('/load-more/<string:object_type>', methods=['GET'])
def load_more(object_type):
    utils.log_activity(f"loading more {object_type}")

    #define a new results dict for publications to take new publications from the search results stored in the session
    results = {}
    results[object_type] = session['search-results'][object_type]

    total_search_results = session['total_search_results'][object_type]
    displayed_search_results = session['displayed_search_results'][object_type]
    number_of_records_to_append_on_lazy_load = int(app.config["NUMBER_OF_RECORDS_TO_APPEND_ON_LAZY_LOAD"])       
    results[object_type] = results[object_type][displayed_search_results:displayed_search_results+number_of_records_to_append_on_lazy_load]
    session['displayed_search_results'][object_type] = displayed_search_results+number_of_records_to_append_on_lazy_load
    return render_template(f'partials/search-results/{object_type}.html', results=results) 


@app.route('/are-embeddings-generated', methods=['GET'])
@utils.timeit
def are_embeddings_generated():
    #Check the embeddings readiness only if the chatbot feature is enabled otherwise return False
    if (app.config['CHATBOT']['chatbot_enable']):
        print('are_embeddings_generated')
        uuid = session['search_uuid']
        chatbot_server = app.config['CHATBOT']['chatbot_server'] 
        are_embeddings_generated = app.config['CHATBOT']['endpoint_are_embeddings_generated'] 
        request_url = f"{chatbot_server}{are_embeddings_generated}/{uuid}"    
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", request_url, headers=headers)    
        json_response = response.json()
        print('json_response:', json_response)
        return str(json_response['file_exists'])
    else:
        return str(True)

@app.route('/get-chatbot-answer', methods=['GET'])
@utils.timeit
def get_chatbot_answer():
    question = request.args.get('question')
    utils.log_activity(f"User asked the chatbot: {question}")
    search_uuid = session['search_uuid']
    answer = chatbot.getAnswer(app=app, question=question, search_uuid=search_uuid)
    
    return answer


@app.route('/publication-details/<path:identifier_with_type>', methods=['GET'])
@utils.timeit
@utils.set_cookies
def publication_details(identifier_with_type):

    utils.log_activity(f"loading publication details page: {identifier_with_type}")    
    identifier_type = identifier_with_type.split(':',1)[0] # as of now this is hardcoded as 'doi'
    identifier = identifier_with_type.split(':',1)[1]
      
    sources = []
    for module in app.config['DATA_SOURCES']:
        if app.config['DATA_SOURCES'][module].get('get-publication-endpoint','').strip() != "":
            sources.append(module)

    for source in sources:
        module_name = app.config['DATA_SOURCES'][source].get('module', '')              

    threads = []  
    publications = []

    for source in sources:
        module_name = app.config['DATA_SOURCES'][source].get('module', '')            
        t = threading.Thread(target=(importlib.import_module(f'sources.{module_name}')).get_publication, args=(source, "https://doi.org/"+identifier, publications,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # publications_json = jsonify(publications)
    # with open('publications.json', 'w', encoding='utf-8') as f:
    #     json.dump(jsonify(publications).json, f, ensure_ascii=False, indent=4)

    if (len(publications) == 1): #forward the only publication record received from one of the sources
        response = make_response(render_template('publication-details.html', publication=publications[0]))
    else: 
        #merge more than one publications record into one publication
        merged_publication = gen_ai.generate_response_with_openai(jsonify(publications).json)
        response = make_response(render_template('publication-details.html', publication=merged_publication))

    return response

@app.route('/publication-details-references/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_references(doi):
    print("doi:", doi)  
    source = "crossref - Publications" 
    module_name = "crossref_publications"     
    publication = importlib.import_module(f'sources.{module_name}').get_publication_references(source=source, doi=doi)
    response = make_response(render_template('partials/publication-details/references.html', publication=publication))    
    return response

@app.route('/publication-details-recommendations/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_recommendations(doi):
    print("DOI:", doi)    
    module_name = "semanticscholar"
    publications = importlib.import_module(f'sources.{module_name}').get_recommendations_for_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/recommendations.html', publications=publications))
    print("response:", response)
    return response

@app.route('/publication-details-citations/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_citations(doi):
    print("DOI:", doi)  
    module_name = "semanticscholar"  
    publications = importlib.import_module(f'sources.{module_name}').get_citations_for_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/citations.html', publications=publications))
    print("response:", response)
    return response

@app.route('/resource-details')
@utils.timeit
@utils.set_cookies
def resource_details():
    response = make_response(render_template('resource-details.html'))  
    return response


@app.route('/researcher-details/<path:identifier_with_type>', methods=['GET'])
@utils.timeit
@utils.set_cookies
def researcher_details(identifier_with_type):

    utils.log_activity(f"loading researcher details page: {identifier_with_type}")    
    identifier_type = identifier_with_type.split(':',1)[0] # as of now this is hardcoded as 'orcid'
    identifier = identifier_with_type.split(':',1)[1]
      
    sources = []
    for module in app.config['DATA_SOURCES']:
        if app.config['DATA_SOURCES'][module].get('get-researcher-endpoint','').strip() != "":
            sources.append(module)

    for source in sources:
        module_name = app.config['DATA_SOURCES'][source].get('module', '')              

    threads = []  
    researchers = []

    for source in sources:
        module_name = app.config['DATA_SOURCES'][source].get('module', '')            
        t = threading.Thread(target=(importlib.import_module(f'sources.{module_name}')).get_researcher, args=(source, identifier, researchers,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # publications_json = jsonify(publications)
    # with open('publications.json', 'w', encoding='utf-8') as f:
    #     json.dump(jsonify(publications).json, f, ensure_ascii=False, indent=4)

    if (len(researchers) == 1): #forward the only publication record received from one of the sources
        response = make_response(render_template('researcher-details.html', researcher=researchers[0]))
        session['researcher:'+identifier] = jsonify(researchers[0]).json
    else: 
        #merge more than one researchers record into one researcher
        merged_researcher = gen_ai.generate_response_with_openai(jsonify(researchers).json)
        response = make_response(render_template('researcher-details.html', researcher=merged_researcher))
        session['researcher:'+identifier] = merged_researcher

    return response

@app.route('/generate-researcher-about-me/<string:orcid>', methods=['GET'])
@utils.handle_exceptions
def generate_researcher_about_me(orcid):
    researcher_about_me = gen_ai.generate_researcher_about_me(session['researcher:'+orcid])
    return jsonify(summary=f'{researcher_about_me}')


@app.route('/generate-researcher-banner/<string:orcid>', methods=['GET'])
@utils.handle_exceptions
def generate_researcher_banner(orcid): 
    generated_banner = gen_ai.generate_researcher_banner(session['researcher:'+orcid])
    if generated_banner == "":
        import base64
        with open('static/images/researcher-default-banner.jpg', "rb") as fh:
            generated_banner = base64.b64encode(fh.read()).decode()
    return jsonify(generated_banner = f'data:image/jpeg;base64,{generated_banner}')



@app.route('/organization-details/<string:organization_id>/<string:organization_name>', methods=['GET'])
@utils.timeit
@utils.set_cookies
def organization_details(organization_id, organization_name):
    try:

        # Create a response object
        """ response = make_response()

        # Set search-session cookie to the session cookie value of the first visit
        if request.cookies.get('search-session') is None:
            if request.cookies.get('session') is None:
                response.set_cookie('search-session', str(uuid.uuid4()))
            else:
                response.set_cookie('search-session', request.cookies['session'])"""

        # Call the org_details function from the gepris module to fetch organization details by id
        organization, sub_organization, sub_project = org_details(organization_id, organization_name)

        if organization or sub_organization or sub_project:
            # Render the organization-details.html template
            return render_template('organization-details.html', organization=organization,
                                   sub_organization=sub_organization, sub_project=sub_project)
        else:
            # Handle the case where organization details are not found (e.g., return a 404 page)
            return render_template('error.html', error_message='Organization details not found.')

    except ValueError as ve:
        return render_template('error.html', error_message=str(ve))
    except Exception as e:
        return render_template('error.html', error_message='An error occurred: ' + str(e))


@app.route('/events-details')
@utils.timeit
@utils.set_cookies
def events_details():
    response = make_response(render_template('events-details.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/project-details')
@utils.timeit
@utils.set_cookies
def project_details():
    response = make_response(render_template('project-details.html'))
    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response

@app.route('/digital-obj-details/<path:identifier_with_type>', methods=['GET'])
@utils.timeit
@utils.set_cookies
def digital_obj_details(identifier_with_type):

    utils.log_activity(f"loading digital obj details page: {identifier_with_type}")    
    identifier_type = identifier_with_type.split(':',1)[0] # as of now this is hardcoded as 'doi'
    identifier = identifier_with_type.split(':',1)[1]
    pass   




#endregion



#region Control Panel

@app.route('/control-panel/dashboard')
def dashboard():
    current_month_users, current_month_users_count, current_year_users, current_year_users_count = utils.generate_registered_users_summaries()
    current_month_visitors, current_month_visitors_count, current_year_visitors, current_year_visitors_count = utils.generate_visitors_summaries()
    current_year_ua_series, current_year_ua_labels, current_year_ua_count = utils.generate_user_agent_family_summary()
    current_year_os_series, current_year_os_labels, current_year_os_count = utils.generate_operating_system_family_summary()
    current_year_search_terms = utils.generate_search_term_summary()
    
    return render_template(f'control-panel/dashboard.html', **locals())

@app.route('/control-panel/activity-log', defaults={'report_date_range': None})
@app.route('/control-panel/activity-log/<report_date_range>')
def activity_log(report_date_range):
    print(f"{report_date_range=}")
    start_date, end_date = utils.parse_report_date_range(report_date_range)
    user_activities = utils.get_user_activities(start_date, end_date)
    return render_template(f'control-panel/activity-log.html', 
                           user_activities=user_activities,
                           report_daterange=f"{start_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])} - {end_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])}") 

@app.route('/control-panel/user-agent-log', defaults={'report_date_range': None})
@app.route('/control-panel/user-agent-log/<report_date_range>')
def user_agent_log(report_date_range):
    print(f"{report_date_range=}")
    start_date, end_date = utils.parse_report_date_range(report_date_range)
    user_agents = utils.get_user_agents(start_date, end_date)
    return render_template(f'control-panel/agent-log.html', 
                           user_agents=user_agents,
                           report_daterange=f"{start_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])} - {end_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])}")  

@app.route('/control-panel/event-log', defaults={'report_date_range': None})
@app.route('/control-panel/event-log/<report_date_range>')
def event_log(report_date_range):
    print(f"{report_date_range=}")
    start_date, end_date = utils.parse_report_date_range(report_date_range)
    events = utils.get_events(start_date, end_date)    
    return render_template(f'control-panel/event-log.html', 
                           events=events, 
                           report_daterange=f"{start_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])} - {end_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])}") 

@app.route('/control-panel/event-log/delete-event/<string:event_id>')
def delete_event(event_id):
    utils.delete_event(event_id)
    return "Event has been deleted" 


@app.route('/control-panel/registered-users', defaults={'report_date_range': None})
@app.route('/control-panel/registered-users/<report_date_range>')
def registered_users(report_date_range):
    print(f"{report_date_range=}")
    start_date, end_date = utils.parse_report_date_range(report_date_range)
    users = utils.get_users(start_date, end_date)
    return render_template(f'control-panel/registered-users.html', 
                           users=users,
                           report_daterange=f"{start_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])} - {end_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])}") 

@app.route('/control-panel/registered-users/delete-user/<string:user_id>')
def delete_user(user_id):
    utils.delete_user(user_id)
    return "User has been deleted" 

@app.route('/control-panel/load-test-users')
def load_test_users():
    for i in range(101,500):
        user = User()
        user.first_name = "First Name " +str(i)
        user.last_name = "Last Name " +str(i)
        user.email = "user.email."+str(i)+"@example.com"
        user.set_password("1234")
        utils.add_user(user)

    return "users created"


@app.route('/control-panel/search-term-log', defaults={'report_date_range': None})
@app.route('/control-panel/search-term-log/<report_date_range>')
def search_term_log(report_date_range):
    print(f"{report_date_range=}")
    start_date, end_date = utils.parse_report_date_range(report_date_range)
    search_terms = utils.get_search_terms(start_date, end_date)
    return render_template(f'control-panel/search-term-log.html', 
                           search_terms=search_terms,
                           report_daterange=f"{start_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])} - {end_date.strftime(app.config['DATE_FORMAT_FOR_REPORT'])}") 



#endregion

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)
