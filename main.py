
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



from flask import Flask, render_template, request, make_response, session, jsonify, redirect, flash, url_for, current_app, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_session import Session

from config import Config

# from objects import Person, Zenodo, Article, Dataset, Presentation, Poster, Software, Video, Image, Lesson, Institute, Funder, Publisher, Gesis, Cordis, Orcid, Gepris
from objects import Article, Organization, Person, Dataset, Project

from sources import dblp_publications, openalex_publications, zenodo, wikidata_publications, wikidata_researchers, openalex_researchers
from sources import resodate, oersi, ieee, eudat, openaire_products
from sources import dblp_researchers
from sources import crossref, semanticscholar
from sources import cordis, gesis, orcid, gepris, eulg, re3data, orkg

from chatbot import chatbot

import details_page
from sources.gepris import org_details
import utils
import deduplicator

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
def format_digital_obj_url(value):
    sources_list = []
    for source in value.source:
        source_dict = {}
        source_dict['doi'] = value.identifier
        source_dict['sname'] = source.name
        source_dict['sid'] = source.identifier
        sources_list.append(source_dict)
    return json.dumps(sources_list)
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
    return jsonify(ping="NFDI4DS Gateway is up and running :) ")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User()
        user.email = form.email.data
        res_flag, user = utils.get_user_by_email(user)        
        if not res_flag or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
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
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)



# authization code copied from https://github.com/miguelgrinberg/flask-oauth-example
@app.route('/authorize/<provider>')
def oauth2_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))

    provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
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

    provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
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
        flash('Your changes have been saved.')
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
    data_sources_list = current_app.config['DATA_SOURCES']
    form.data_sources.choices = [(source, source) for source in current_app.config['DATA_SOURCES'].keys()]
    # if it's a post request and we validated successfully
    if request.method == 'POST' and form.validate_on_submit():
        # get our choices again, could technically cache these in a list if we wanted but w/e
        all_sources = current_app.config['DATA_SOURCES'].keys()
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
    else:
        # tell the form what's already selected
        form.data_sources.data = [source for source in current_user.included_data_sources.split('; ')]
    return render_template('preferences.html', title='Preferences', form=form)


@app.route('/')
def index():
    
    flash("testing message in base.html", category='info')
    flash("testing message 2 in base.html", category='warning')

    utils.log_activity("loading index page")

    if (utils.env_config["OPENAI_API_KEY"] == ""):
        return make_response(render_template('error.html',error_message='Environment variables are not set. Kindly set all the required variables.'))

    response = make_response(render_template('index.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response

@app.route('/results', methods=['POST', 'GET'])
@utils.timeit
def search_results():

    utils.log_activity("loading search results")

    logger.info('search server call initiated.')
    # The search-session cookie setting can still be None if a user enters the
    # /sources endpoint directly without going to / first!!!
    logger.debug(
        f'Search session {request.cookies.get("search-session")} '
        f'searched for "{request.args.get("txtSearchTerm")}"'
    )

    results = {
        'publications': [],
        'researchers': [],
        'resources': [],
        'organizations': [],
        'events': [],
        'fundings': [],
        'others': [],
        'timedout_sources': []
    }

    if request.method == 'GET':
        search_term = request.args.get('txtSearchTerm')
        session['search-term'] = search_term

        for k in results.keys(): results[k] = []
        threads = []

        # add all the sources here in this list; for simplicity we should use the exact module name
        # ensure the main method which execute the search is named "search" in the module         
        sources = [dblp_publications, openalex_publications, zenodo, wikidata_publications, resodate, oersi, ieee,
                   eudat, openaire_products, re3data, orkg, openalex_researchers]
        # sources = [openalex_publications]
        for source in sources:
            t = threading.Thread(target=source.search, args=(search_term, results,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
            # print(t.is_alive())

        # deduplicator.convert_publications_to_csv(results["publications"])
        # results["publications"] = deduplicator.perform_entity_resolution_publications(results["publications"])

        # sort all the results in each category
        results["publications"] = utils.sort_search_results(search_term, results["publications"])  
        results["researchers"] = utils.sort_search_results(search_term, results["researchers"])             
        
        #store the search results in the session
        session['search-results'] = copy.deepcopy(results)        

        # Chatbot - push search results to chatbot server for embeddings generation
        if (utils.config['chatbot_feature_enable']):

            # Convert a UUID to a 32-character hexadecimal string
            search_uuid = uuid.uuid4().hex
            session['search_uuid'] = search_uuid
            
            def send_search_results_to_chatbot(search_uuid: str):
                print('request is about to start')
                chatbot_server = utils.config['chatbot_server'] 
                save_docs_with_embeddings = utils.config['endpoint_save_docs_with_embeddings'] 
                request_url = f'{chatbot_server}{save_docs_with_embeddings}/{search_uuid}'        
                response = requests.post(request_url, json=json.dumps(results, default=vars))
                response.raise_for_status() 
                print('request completed')

            # create a new daemon thread
            chatbot_thread = threading.Thread(target=send_search_results_to_chatbot, args=(search_uuid,), daemon=True)
            # start the new thread
            chatbot_thread.start()
            # sleep(1)
        

        # on the first page load, only push top 20 records in each category
        number_of_records_to_show_on_page_load = int(utils.config["number_of_records_to_show_on_page_load"])        
        total_results = {} # the dict to keep the total number of search results 
        displayed_results = {} # the dict to keep the total number of search results currently displayed to the user
        
        for k, v in results.items():
            logger.info(f'Got {len(v)} {k}')
            total_results[k] = len(v)
            results[k] = v[:number_of_records_to_show_on_page_load]
            displayed_results[k] = len(results[k])

        results["timedout_sources"] = list(set(results["timedout_sources"]))
        logger.info('Following sources got timed out:' + ','.join(results["timedout_sources"]))  

        session['total_search_results'] = total_results
        session['displayed_search_results'] = displayed_results 
        
        template_response = render_template('results.html', results=results, total_results=total_results, search_term=search_term)    
        logger.info('search server call completed - after render call')

        return template_response

@app.route('/load-more-publications', methods=['GET'])
def load_more_publications():
    print('load more publications')

    #define a new results dict for publications to take new publications from the search results stored in the session
    results = {}
    results['publications'] = session['search-results']['publications']

    total_search_results_publications = session['total_search_results']['publications']
    displayed_search_results_publications = session['displayed_search_results']['publications']
    number_of_records_to_append_on_lazy_load = int(utils.config["number_of_records_to_append_on_lazy_load"])       
    results['publications'] = results['publications'][displayed_search_results_publications:displayed_search_results_publications+number_of_records_to_append_on_lazy_load]
    session['displayed_search_results']['publications'] = displayed_search_results_publications+number_of_records_to_append_on_lazy_load
    return render_template('components/publications.html', results=results)  

@app.route('/load-more-researchers', methods=['GET'])
def load_more_researchers():
    print('load more researchers')

    #define a new results dict for researchers to take new researchers from the search results stored in the session
    results = {}
    results['researchers'] = session['search-results']['researchers']

    total_search_results_researchers = session['total_search_results']['researchers']
    displayed_search_results_researchers = session['displayed_search_results']['researchers']
    number_of_records_to_append_on_lazy_load = int(utils.config["number_of_records_to_append_on_lazy_load"])       
    results['researchers'] = results['researchers'][displayed_search_results_researchers:displayed_search_results_researchers+number_of_records_to_append_on_lazy_load]
    session['displayed_search_results']['researchers'] = displayed_search_results_researchers+number_of_records_to_append_on_lazy_load
    return render_template('components/researchers.html', results=results)     

@app.route('/are-embeddings-generated', methods=['GET'])
def are_embeddings_generated():

    #Check the embeddings readiness only if the chatbot feature is enabled otherwise return False
    if (utils.config['chatbot_feature_enable']):
        print('are_embeddings_generated')
        uuid = session['search_uuid']
        chatbot_server = utils.config['chatbot_server'] 
        are_embeddings_generated = utils.config['endpoint_are_embeddings_generated'] 
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
def get_chatbot_answer():
    print('get chatbot answer')

    question = request.args.get('question')
    print('User asked:', question)

    # context = session['search-results']
    # answer = chatbot.getAnswer(question=question, context=context)

    search_uuid = session['search_uuid']
    answer = chatbot.getAnswer(question=question, search_uuid=search_uuid)
    
    return answer


# @app.route('/chatbot')
# def chatbot():
#     response = make_response(render_template('chatbot.html'))

#     # Set search-session cookie to the session cookie value of the first visit
#     if request.cookies.get('search-session') is None:
#         if request.cookies.get('session') is None:
#             response.set_cookie('search-session', str(uuid.uuid4()))
#         else:
#             response.set_cookie('search-session', request.cookies['session'])

#     return response



from urllib.parse import unquote
import ast

@app.route('/publication-details/<path:sources>', methods=['GET'])
@utils.timeit
def publication_details(sources):

    sources = unquote(sources)
    sources = ast.literal_eval(sources)    
    for source in sources:
        doi = source['doi']
    
    publication = openalex_publications.get_publication(doi="https://doi.org/"+doi)
    response = make_response(render_template('publication-details.html', publication=publication))

    print("response:", response)
    return response

@app.route('/publication-details-references/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_references(doi):
    print("doi:", doi)    
    
    publication = crossref.get_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/references.html', publication=publication))

    print("response:", response)
    return response

@app.route('/publication-details-recommendations/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_recommendations(doi):
    print("DOI:", doi)    
    publications = semanticscholar.get_recommendations_for_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/recommendations.html', publications=publications))
    print("response:", response)
    return response

@app.route('/publication-details-citations/<path:doi>', methods=['GET'])
@utils.timeit
def publication_details_citations(doi):
    print("DOI:", doi)    
    publications = semanticscholar.get_citations_for_publication(doi=doi)
    response = make_response(render_template('partials/publication-details/citations.html', publications=publications))
    print("response:", response)
    return response

@app.route('/resource-details')
def resource_details():
    response = make_response(render_template('resource-details.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/researcher-details/<string:index>', methods=['GET'])
def researcher_details(index):
    # index = json.loads(index)
    # for result in results['researchers']:
    #     if result.source[0].identifier.replace("https://openalex.org/", "") == index[0]['sid']:
    #         researcher = result
    #         break
    # logger.info(f'Found researcher {researcher}')
    researcher = openalex_researchers.get_researcher_details(index)
    response = make_response(render_template('researcher-details.html',researcher=researcher))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response

@app.route('/researcher-banner/<string:index>', methods=['GET'])
def researcher_banner(index):
    pass
    # logger.info(f'Fetching details for researcher with index {index}')
    # for result in results['researchers']:
    #     if result.list_index == index:
    #         researcher = result
    #         break
    # # logger.info(f'Found researcher {researcher}')
    # researcher = openalex_researchers.get_researcher_banner(researcher)
    # if researcher.banner == "":
    #     return jsonify()
    # return jsonify(imageUrl = f'data:image/jpeg;base64,{researcher.banner}')


@app.route('/organization-details/<string:organization_id>/<string:organization_name>', methods=['GET'])
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
def events_details():
    response = make_response(render_template('events-details.html'))

    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/fundings-details')
def fundings_details():
    response = make_response(render_template('fundings-details.html'))
    # Set search-session cookie to the session cookie value of the first visit
    if request.cookies.get('search-session') is None:
        if request.cookies.get('session') is None:
            response.set_cookie('search-session', str(uuid.uuid4()))
        else:
            response.set_cookie('search-session', request.cookies['session'])

    return response


@app.route('/details', methods=['POST', 'GET'])
def details():
    if request.method == 'GET':
        # data_type = request.args.get('type')
        details = {}
        links = {}
        name = ''
        search_term = request.args.get('searchTerm')
        if search_term.startswith('https://openalex.org/'):
            details, links, name = details_page.search_openalex(search_term)
        elif search_term.startswith('https://dblp'):
            details, links, name = details_page.search_dblp(search_term)
        elif search_term.startswith('http://www.wikidata.org'):
            details, links, name = details_page.search_wikidata(search_term)
        elif search_term.startswith('https://orcid.org/'):
            details, links, name = details_page.search_orcid(search_term)
        return render_template('details.html', search_term=search_term, details=details, links=links, name=name)


#endregion

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)
