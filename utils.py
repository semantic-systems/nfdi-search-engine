import os
import uuid
# import extruct
from objects import Article, Person, Author
# import wikipedia
from bs4 import BeautifulSoup
import traceback
import inspect
from flask import Flask, request, session
import pandas as pd

def clean_json(value):
    """
    Recursively remove all None values from dictionaries and lists, and returns
    the result as a new dictionary or list.
    """
    if isinstance(value, list):
        return [clean_json(x) for x in value if x is not None]
    elif isinstance(value, dict):
        return {
            key: clean_json(val)
            for key, val in value.items()
            if val is not None
        }
    else:
        return value

# def extract_metadata(text):
#     """
#     Extract all metadata present in the page and return a dictionary of metadata lists.

#         Initially authored by Ricardo Usbeck

#     Args:

#     Returns:
#         metadata (dict): Dictionary of json-ld, microdata, and opengraph lists.
#         Each of the lists present within the dictionary contains multiple dictionaries.
#     """

#     metadata = extruct.extract(text,
#                                uniform=True,
#                                syntaxes=['json-ld',
#                                          'microdata',
#                                          'opengraph'])
#     return metadata

def is_author_in(name, authors):
    """
    Verifies if the author is already in the results
    Args:
        name: name of the author
        authors: list of the results

    Returns:
        True if it's already there and False if not

    """
    for author in authors:
        if type(author) is not Person:
            continue
        if author.name == name:
            return author
    return None

def is_article_in(title, articles):
    """
        Verifies if the paper is already in the results
        Args:
            title: name of the paper
            articles: list of the results

        Returns:
            True if it's already there and False if not

        """
    for article in articles:
        if type(article) is not Article:
            continue
        if article.title == title:
            return article
    return None

# def read_wikipedia(title):
#     wikipedia.set_lang("en")
#     try:
#         summary_text = wikipedia.summary(title, 3, redirect=True)
#     except:
#         return ""
#     return summary_text

def remove_html_tags(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.text.strip()

def remove_line_tags(text):
    return text.replace('\n', ' ').replace('\t', ' ')

def generate_string_from_keys(dictionary):
    keys_list = list(dictionary.keys())
    keys_string = " ".join(keys_list)
    return keys_string

from dateparser import parse
from datetime import timedelta
def parse_date(date_str):
    try:
        parsed_date_str = parse(date_str).strftime("%Y-%m-%d")
        return parsed_date_str
    except (TypeError, ValueError):
        print(f"original date str: {date_str}")
        return ""

def parse_report_date_range(report_date_range):
    if report_date_range:
        start_date =  datetime.strptime(report_date_range.partition(' - ')[0], current_app.config['DATE_FORMAT_FOR_REPORT'])
        end_date =  datetime.strptime(report_date_range.partition(' - ')[2], current_app.config['DATE_FORMAT_FOR_REPORT'])      
    else:
        # default the date range filter to last 7 days
        # start_date = (datetime.now()+timedelta(days=-6))
        start_date = datetime.now()
        end_date = datetime.now()
    return start_date, end_date 

def parse_date_range_for_elastic(start_date, end_date):
    start_date = start_date.strftime(current_app.config['DATE_FORMAT_FOR_ELASTIC'])
    # Add a day to end-date so it can include that the documents for that day too
    end_date = (end_date+timedelta(days=0)).strftime(current_app.config['DATE_FORMAT_FOR_ELASTIC'])
    return start_date, end_date  


# def sort_results_publications(results):
#     def custom_sort_key(obj):    
#         desc = getattr(obj, 'description', '') 
#         pub_date = getattr(obj, 'datePublished', '0000-00-00') 
#         if desc == '':
#             return (0, pub_date)
#         return (1, pub_date)

#     return sorted(results, key=custom_sort_key, reverse=True)

from rank_bm25 import BM25Plus
def sort_search_results(search_term, search_results):    

    tokenized_results = [str(result).lower().split(" ") for result in search_results]
    if len(tokenized_results) > 0:
        bm25 = BM25Plus(tokenized_results)
    
        tokenized_query = search_term.lower().split(" ")
        doc_scores = bm25.get_scores(tokenized_query)
        
        for idx, doc_score in enumerate(doc_scores):
            search_results[idx].rankScore = doc_score

    search_results = sorted(search_results, key=lambda x: x.rankScore, reverse=True)
    # return sorted(search_results, key=lambda x: x.rankScore, reverse=True)

def split_authors(authors_names, seperator, authors_list):
    authors = authors_names.split(seperator)
    for author in authors:
        _author = Author()
        _author.type = 'Person'
        _author.name = author
        authors_list.append(_author)  

#region User Activity Logging
from elasticsearch import Elasticsearch, exceptions
es_client = Elasticsearch(
    os.environ.get("ELASTIC_SERVER", ""),  # Elasticsearch endpoint
    basic_auth=(os.environ.get("ELASTIC_USERNAME", ""), os.environ.get("ELASTIC_PASSWORD", "")),
    # api_key="aWozWnVKQUItaEJISkZmZS1hd1c6WFQ3OUdZdUlTZFdZUDlqcmVGVkhvdw==",
) 

from enum import Enum
class ES_Index(Enum):
    user_activity_log = 1
    user_agent_log = 2
    users = 3
    event_logs = 4
    search_term_log = 5

# create all the indices if they don't exist
# ignore 400 caused by IndexAlreadyExistsException when creating an index
for idx in ES_Index:
    """Create the given ElasticSearch index and ignore error if it already exists"""
    try:
        es_client.indices.create(index=idx.name)
    except exceptions.RequestError as ex:
        if ex.error == 'resource_already_exists_exception':
            pass # Index already exists. Ignore.
        else: # Other exception - raise it
            raise ex
    

from datetime import datetime, timezone
from flask import request, current_app
from flask_login import current_user
from ua_parser import user_agent_parser

def get_client_ip():
    client_ip = request.remote_addr
    if 'X-Forwarded-For' in request.headers:
        client_ip = request.headers.getlist('X-Forwarded-For')[0]
    return client_ip

def log_activity(user_activity): 
    es_client.index(
        index=ES_Index.user_activity_log.name,        
        document={
            "timestamp": datetime.now(timezone.utc),
            "user_email": session.get('current-user-email', ""),
            "session_id": session.get('gateway-session-id', ""), 
            "visitor_id": "", #this will be updated later via ajax call   
            "url": request.url,
            "host": request.host,
            "url_root": request.root_url,
            "base_url": request.base_url,            
            "path": request.path,
            "description": user_activity,
        }
    )

def get_user_activities(start_date, end_date):
    start_date, end_date = parse_date_range_for_elastic(start_date, end_date)
    result = es_client.search(index=ES_Index.user_activity_log.name, 
                              size=10000,
                              query = {
                                    "range": { 
                                        "timestamp": {
                                            "gte":start_date, 
                                            "lte":end_date,
                                        }
                                    }
                                },
                                sort=[{ "timestamp" : "desc" }])   
    return result["hits"]["hits"]

def log_search_term(search_term): 
    es_client.index(
        index=ES_Index.search_term_log.name,        
        document={
            "timestamp": datetime.now(timezone.utc),
            "user_email": session.get('current-user-email', ""),
            "session_id": session.get('gateway-session-id', ""), 
            "visitor_id": "", #this will be updated later via ajax call   
            "url": request.url,            
            "search_term": search_term,
        }
    )

def get_search_terms(start_date, end_date):
    start_date, end_date = parse_date_range_for_elastic(start_date, end_date)
    result = es_client.search(index=ES_Index.search_term_log.name, 
                            size=10000,
                            query = {
                                "range": { 
                                    "timestamp": {
                                        "gte":start_date, 
                                        "lte":end_date,
                                    }
                                }
                            },
                            sort=[{ "timestamp" : "desc" }])    
    return result["hits"]["hits"]

def log_agent():    
    
    # first check if the agent details already exist for this session id, if not then add them, else update that record
    result = es_client.search(index=ES_Index.user_agent_log.name, query={"match": {"session_id": {"query": session.get('gateway-session-id','')}}})
    result_rec_count = int(result["hits"]["total"]["value"])       
    if result_rec_count > 0:
        hit = result["hits"]["hits"][0] 
        es_client.update(
            index=ES_Index.user_agent_log.name, 
            id=hit['_id'],   
            doc={            
                "timestamp_updated": datetime.now(timezone.utc),
                "url": request.url,
            }
        )
    else:
        #extract user agent details from the request headers
        user_agent_string = request.headers.get("user-agent") 
        user_agent_parsed = user_agent_parser.Parse(user_agent_string)        

        es_client.index(
            index=ES_Index.user_agent_log.name,        
            document={
                "timestamp_created": datetime.now(timezone.utc),
                "timestamp_updated": datetime.now(timezone.utc),
                "user_email": session.get('current-user-email', ""),
                "session_id": session.get('gateway-session-id', ""),
                "visitor_id": "", #this will be updated later via ajax call   
                # "ip_address": request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
                "ip_address": get_client_ip(),
                "user_agent": user_agent_string,
                "device_family": user_agent_parsed.get('device',{}).get('family',""),
                "device_brand":  user_agent_parsed.get('device',{}).get('major',""),
                "device_model":  user_agent_parsed.get('device',{}).get('minor',""),
                "os_family": user_agent_parsed.get('os',{}).get('family',""),
                "os_major":  user_agent_parsed.get('os',{}).get('major',""),
                "os_minor":  user_agent_parsed.get('os',{}).get('minor',""),
                "os_patch":  user_agent_parsed.get('os',{}).get('patch',""),
                "os_patch_minor": user_agent_parsed.get('os',{}).get('patch_minor',""),
                "user_agent_family": user_agent_parsed.get('user_agent',{}).get('family',""),
                "user_agent_major":  user_agent_parsed.get('user_agent',{}).get('major',""),
                "user_agent_minor":  user_agent_parsed.get('user_agent',{}).get('minor',""),
                "user_agent_patch":  user_agent_parsed.get('user_agent',{}).get('patch',""),           
                "user_agent_language": request.user_agent.language,
                "url": request.url,
                # "host": request.host,
                # "url_root": request.root_url,
                # "base_url": request.base_url,            
                # "path": request.path,
            }
        )

def get_user_agents(start_date, end_date, timestamp_filter="timestamp_updated"):
    start_date, end_date = parse_date_range_for_elastic(start_date, end_date)
    result = es_client.search(index=ES_Index.user_agent_log.name, 
                              size=10000,
                              query = {
                                    "range": { 
                                        timestamp_filter: {
                                            "gte":start_date, 
                                            "lte":end_date,
                                        }
                                    }
                                },
                                sort=[{ timestamp_filter : "desc" }])  
    return result["hits"]["hits"]

def log_event(type: str = "info", filename: str = None, method: str = None, args = None, kwargs = None, message: str = None, traceback = None):

    if not filename:
        caller_frame = inspect.stack()[1]
        caller_filename_full = caller_frame.filename
        filename = os.path.splitext(os.path.basename(caller_filename_full))[0]
    
    if not method:
        method = inspect.stack()[1][3]

    es_client.index(
        index=ES_Index.event_logs.name,        
        document={
            "timestamp": datetime.now(timezone.utc),
            "type": type,
            "filename": filename,
            "method": method,
            "args": args,
            "kwargs": kwargs,
            "message": message,
            "traceback": traceback
        }
    )

def get_events(start_date, end_date, log_type):
    start_date, end_date = parse_date_range_for_elastic(start_date, end_date)
    # result = es_client.search(index=ES_Index.event_logs.name, query={"match": {"type": {"query": "error"}}}, size=100, sort=[{ "timestamp" : "asc" }]) 
    result = es_client.search(index=ES_Index.event_logs.name, 
                            size=10000,
                            query={
                                "bool" : {
                                    "must" : [
                                        { "term" : { "type.keyword" : log_type } },
                                        { "range": { "timestamp": { "gte":start_date, "lte":end_date }} }                                        
                                    ]
                                } 
                            },
                            sort=[{ "timestamp" : "desc" }])    
    return result["hits"]["hits"]

def delete_event(event_id:str):
    es_client.delete(index=ES_Index.event_logs.name, id=event_id)

def update_visitor_id(visitor_id:str):   

    result = es_client.search(index=ES_Index.user_activity_log.name,
                            query={
                                "bool" : {
                                    "must" : [
                                        { "term" : { "session_id.keyword" : session.get('gateway-session-id', '') } }, 
                                        { "term" : { "visitor_id.keyword" : "" } } 
                                    ]
                                } 
                            })                            
    result_rec_count = int(result["hits"]["total"]["value"])  
    # print(f"user_activity_log - {result_rec_count=}")     
    if result_rec_count > 0:
        hits = result["hits"]["hits"]
        for hit in hits:
            es_client.update(
                index=ES_Index.user_activity_log.name, 
                id=hit['_id'],   
                doc={            
                    "visitor_id": visitor_id,
                }
            )

    result = es_client.search(index=ES_Index.search_term_log.name,
                            query={
                                "bool" : {
                                    "must" : [
                                        { "term" : { "session_id.keyword" : session.get('gateway-session-id', '') } }, 
                                        { "term" : { "visitor_id.keyword" : "" } } 
                                    ]
                                } 
                            })                            
    result_rec_count = int(result["hits"]["total"]["value"])  
    # print(f"search_term_log - {result_rec_count=}")     
    if result_rec_count > 0:
        hits = result["hits"]["hits"]
        for hit in hits:
            es_client.update(
                index=ES_Index.search_term_log.name, 
                id=hit['_id'],   
                doc={            
                    "visitor_id": visitor_id,
                }
            )

    result = es_client.search(index=ES_Index.user_agent_log.name,
                              query={
                                "bool" : {
                                    "must" : [
                                        { "term" : { "session_id.keyword" : session.get('gateway-session-id', '') } }, 
                                        { "term" : { "visitor_id.keyword" : "" } } 
                                    ]
                                } 
                            })   
    result_rec_count = int(result["hits"]["total"]["value"])  
    # print(f"user_agent_log - {result_rec_count=}")          
    if result_rec_count > 0:
        hits = result["hits"]["hits"]
        for hit in hits:
            es_client.update(
                index=ES_Index.user_agent_log.name, 
                id=hit['_id'],   
                doc={            
                    "visitor_id": visitor_id,
                }
            )


def generate_registered_users_summaries():
    year_start_date = datetime.today().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)  
    current_date = datetime.today()    
    current_year_users = get_users(year_start_date, current_date)

    # generate monthly summary for current year
    df_current_year_users = pd.json_normalize(current_year_users)
    df_current_year_users = df_current_year_users[['_id', '_source.timestamp_created']]
    df_current_year_users = df_current_year_users.rename(columns={'_id': 'id', '_source.timestamp_created': 'timestamp'})    
    # Convert timestamp to datetime object
    df_current_year_users['timestamp'] = pd.to_datetime(df_current_year_users['timestamp'], format='ISO8601')
    # Create a new column for the month
    df_current_year_users['month'] = df_current_year_users['timestamp'].dt.month_name()
    # Group the data by month and count the unique ID's
    grouped_df = df_current_year_users.groupby('month')['id'].nunique()
    # Turn series into DataFrame
    result_df = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'Unique ID count'})
    # Handling months with no data
    all_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    result_df.set_index('month', inplace = True)
    result_df = result_df.reindex(all_months).fillna(0).reset_index()
    result_df = result_df.rename(columns={'month': 'x', 'Unique ID count': 'y'})    
    current_year_users = result_df.to_dict('records')
    current_year_users_count = df_current_year_users.shape[0]


    # generate daily summary for current month 
    month_start_date = pd.to_datetime(datetime.today().replace(day=1, hour=0, minute=0, second=0, microsecond=0), utc=True)
    df_current_month_users = df_current_year_users[(df_current_year_users['timestamp'] > month_start_date)]
    # Create a new column for the day of the month
    df_current_month_users['day'] = df_current_month_users['timestamp'].dt.day
    df_current_month_users['day'] = df_current_month_users['day'].apply(str)
    # Group the data by day and count the unique ID's
    grouped_df = df_current_month_users.groupby('day')['id'].nunique()
    # Turn series into DataFrame
    result_df = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'Unique ID count'})
    # Handling months with no data
    all_days = [str(i).zfill(2) for i in range(1, 32)] # this should actually be limited to the number of days in the current month.
    result_df.set_index('day', inplace = True)
    result_df = result_df.reindex(all_days).fillna(0).reset_index()
    result_df = result_df.rename(columns={'day': 'x', 'Unique ID count': 'y'})    
    current_month_users = result_df.to_dict('records')    
    current_month_users_count = df_current_month_users.shape[0]

    return current_month_users, current_month_users_count, current_year_users, current_year_users_count

def generate_visitors_summaries():
    year_start_date = datetime.today().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)  
    current_date = datetime.today()    
    current_year_visitors = get_user_agents(year_start_date, current_date, timestamp_filter="timestamp_created")

    # generate monthly summary for current year
    df_current_year_visitors = pd.json_normalize(current_year_visitors)
    df_current_year_visitors = df_current_year_visitors[['_source.visitor_id', '_source.timestamp_created']]
    df_current_year_visitors = df_current_year_visitors.rename(columns={'_source.visitor_id': 'id', '_source.timestamp_created': 'timestamp'})    
    # Convert timestamp to datetime object
    df_current_year_visitors['timestamp'] = pd.to_datetime(df_current_year_visitors['timestamp'], format='ISO8601')
    # Create a new column for the month
    df_current_year_visitors['month'] = df_current_year_visitors['timestamp'].dt.month_name()
    # Group the data by month and count the unique ID's
    grouped_df = df_current_year_visitors.groupby('month')['id'].nunique()
    # Turn series into DataFrame
    result_df = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'Unique ID count'})
    # Handling months with no data
    all_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    result_df.set_index('month', inplace = True)
    result_df = result_df.reindex(all_months).fillna(0).reset_index()
    result_df = result_df.rename(columns={'month': 'x', 'Unique ID count': 'y'})    
    current_year_visitors = result_df.to_dict('records')
    current_year_visitors_count = df_current_year_visitors.shape[0]

    # generate daily summary for current month 
    month_start_date = pd.to_datetime(datetime.today().replace(day=1, hour=0, minute=0, second=0, microsecond=0), utc=True)
    df_current_month_visitors = df_current_year_visitors[(df_current_year_visitors['timestamp'] > month_start_date)]
    # Create a new column for the day of the month
    df_current_month_visitors['day'] = df_current_month_visitors['timestamp'].dt.day
    df_current_month_visitors['day'] = df_current_month_visitors['day'].apply(str)
    # Group the data by day and count the unique ID's
    grouped_df = df_current_month_visitors.groupby('day')['id'].nunique()
    # Turn series into DataFrame
    result_df = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'Unique ID count'})
    # Handling months with no data
    all_days = [str(i).zfill(2) for i in range(1, 32)] # this should actually be limited to the number of days in the current month.
    result_df.set_index('day', inplace = True)
    result_df = result_df.reindex(all_days).fillna(0).reset_index()
    result_df = result_df.rename(columns={'day': 'x', 'Unique ID count': 'y'})    
    current_month_visitors = result_df.to_dict('records')    
    current_month_visitors_count = df_current_month_visitors.shape[0]

    return current_month_visitors, current_month_visitors_count, current_year_visitors, current_year_visitors_count

def generate_user_agent_family_summary():
    year_start_date = datetime.today().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)  
    current_date = datetime.today()    
    current_year_visitors = get_user_agents(year_start_date, current_date, timestamp_filter="timestamp_created")

    df_current_year_visitors = pd.json_normalize(current_year_visitors)
    df_current_year_visitors = df_current_year_visitors[['_source.visitor_id', '_source.user_agent_family']]
    df_current_year_visitors = df_current_year_visitors.rename(columns={'_source.visitor_id': 'id', '_source.user_agent_family': 'user_agent'}) 
    df_current_year_visitors.drop_duplicates(inplace=True)

    grouped_df = df_current_year_visitors.groupby('user_agent')['id'].nunique()
    result_df = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'Unique ID count'})    
    current_year_ua_series = result_df['Unique ID count'].tolist()
    current_year_ua_labels = result_df['user_agent'].tolist()
    current_year_ua_count = result_df.shape[0]

    print(f'{current_year_ua_series=}')
    print(f'{current_year_ua_labels=}')

    return current_year_ua_series, current_year_ua_labels, current_year_ua_count

def generate_operating_system_family_summary():
    year_start_date = datetime.today().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)  
    current_date = datetime.today()    
    current_year_visitors = get_user_agents(year_start_date, current_date, timestamp_filter="timestamp_created")

    df_current_year_visitors = pd.json_normalize(current_year_visitors)
    df_current_year_visitors = df_current_year_visitors[['_source.visitor_id', '_source.os_family']]
    df_current_year_visitors = df_current_year_visitors.rename(columns={'_source.visitor_id': 'id', '_source.os_family': 'os'}) 
    df_current_year_visitors.drop_duplicates(inplace=True)

    grouped_df = df_current_year_visitors.groupby('os')['id'].nunique()
    result_df = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'Unique ID count'})    
    current_year_os_series = result_df['Unique ID count'].tolist()
    current_year_os_labels = result_df['os'].tolist()
    current_year_os_count = result_df.shape[0]

    print(f'{current_year_os_series=}')
    print(f'{current_year_os_labels=}')

    return current_year_os_series, current_year_os_labels, current_year_os_count

def generate_search_term_summary():

    year_start_date = datetime.today().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)  
    current_date = datetime.today()    
    current_year_searches = get_search_terms(year_start_date, current_date)

    df_current_year_searches = pd.json_normalize(current_year_searches)
    df_current_year_searches = df_current_year_searches[['_id', '_source.search_term']]
    df_current_year_searches = df_current_year_searches.rename(columns={'_id': 'id', '_source.search_term': 'search_term'}) 
    
    grouped_df = df_current_year_searches.groupby('search_term')['id'].count()
    current_year_search_terms = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'count'}) 

    # sort by count and pick top 10
    current_year_search_terms_top10 = current_year_search_terms.nlargest(10, 'count')

    dict_current_year_search_terms_top10 = current_year_search_terms_top10.set_index('search_term').T.to_dict('list')

    return dict_current_year_search_terms_top10

def generate_traffic_summary():
    year_start_date = datetime.today().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)  
    current_date = datetime.today()    
    current_year_hits = get_user_activities(year_start_date, current_date)

    # generate monthly summary for current year
    df_current_year_hits = pd.json_normalize(current_year_hits)
    df_current_year_hits = df_current_year_hits[['_id', '_source.user_email', '_source.timestamp']]
    df_current_year_hits = df_current_year_hits.rename(columns={'_id': 'id', '_source.user_email': 'email', '_source.timestamp': 'timestamp'})  
    #replace none or null or nan to empty string
    df_current_year_hits.fillna('', inplace=True)
    #convert the email column to category - either registered user or visitor
    df_current_year_hits['user_type'] = df_current_year_hits.apply(lambda x: 'visitor' if x['email'] == '' else 'registered user', axis=1)
    # Convert timestamp to datetime object
    df_current_year_hits['timestamp'] = pd.to_datetime(df_current_year_hits['timestamp'], format='ISO8601')
    # Create a new column for the month
    df_current_year_hits['month'] = df_current_year_hits['timestamp'].dt.month_name()
    # Group the data by month and count the ID's
    grouped_df = df_current_year_hits.groupby(['user_type','month'])['id'].size()
    result_df = pd.DataFrame(grouped_df).reset_index().rename(columns={'id': 'count'})
    
    result_df_registered_users = result_df.loc[result_df['user_type'] == 'registered user']
    result_df_registered_users = result_df_registered_users[['month', 'count']]
    result_df_registered_users.set_index('month', inplace = True)
    
    result_df_visitors = result_df.loc[result_df['user_type'] == 'visitor']
    result_df_visitors = result_df_visitors[['month', 'count']]
    result_df_visitors.set_index('month', inplace = True)
        
    # Handling months with no data
    all_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    result_df_registered_users = result_df_registered_users.reindex(all_months).fillna(0).reset_index()
    result_df_visitors = result_df_visitors.reindex(all_months).fillna(0).reset_index()

    current_year_traffic_registered_users = result_df_registered_users['count'].tolist()
    current_year_traffic_visitors = result_df_visitors['count'].tolist()

    return current_year_traffic_registered_users, current_year_traffic_visitors
    

import random
from time import mktime as mktime
from time import strptime, strftime, localtime    
def str_time_prop(start, end, time_format, prop):
    """Get a time at a proportion of a range of two formatted times.
    start and end should be strings specifying times formatted in the
    given format (strftime-style), giving an interval [start, end].
    prop specifies how a proportion of the interval to be taken after
    start.  The returned time will be in the specified format.
    """
    stime = mktime(strptime(start, time_format))
    etime = mktime(strptime(end, time_format))
    ptime = stime + prop * (etime - stime)
    return strftime(time_format, localtime(ptime))

def random_date(start, end, prop):
    return str_time_prop(start, end, '%Y-%m-%dT%H:%M:%SZ', prop)

def add_user(user):
    es_client.index(
        index=ES_Index.users.name,        
        document={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "password_hash": user.password_hash,
            "timestamp_created": datetime.now(timezone.utc),
            # "timestamp_created": random_date("2024-01-01T00:00:00Z", "2024-10-20T00:00:00Z", random.random()), # this was done when we had to generate test data in dev environment
            "oauth_source": user.oauth_source,
            "included_data_sources": '; '.join(current_app.config['DATA_SOURCES'].keys()), #by default add all the data sources to the included list.
            "excluded_data_sources": user.excluded_data_sources, #by default this should be empty
        }
    )

def update_user(user):
    es_client.update(
        index=ES_Index.users.name, 
        id=user.id,   
        doc={
            "first_name": user.first_name,
            "last_name": user.last_name,
            # "email": user.email,
            "timestamp_updated": datetime.now(timezone.utc),
            "oauth_source": user.oauth_source,
        }
    )

def get_user_by_id(user):
    try:
        hit = es_client.get(index=ES_Index.users.name, id=user.id)
        # user.id = hit['_id']
        user.first_name = hit["_source"].get('first_name','')
        user.last_name = hit["_source"].get('last_name','')
        user.email = hit["_source"].get('email','')
        user.password_hash = hit["_source"].get('password_hash','')
        user.oauth_source = hit["_source"].get('oauth_source','')
        user.included_data_sources = hit["_source"].get("included_data_sources",'')
        user.excluded_data_sources = hit["_source"].get("excluded_data_sources",'')
        return user        
    except exceptions.NotFoundError:
        return None
    except:
        return None

def get_user_by_email(user):
    query={
        "term": {
            "email.keyword": user.email
        }
    }
    result = es_client.search(index=ES_Index.users.name, query=query)
    result_rec_count = int(result["hits"]["total"]["value"])
    if result_rec_count == 1:
        hit = result["hits"]["hits"][0]
        user.id = hit['_id']
        user.first_name = hit["_source"].get('first_name.keyword','')
        user.last_name = hit["_source"].get('last_name','')
        user.email = hit["_source"].get('email','')
        user.password_hash = hit["_source"].get('password_hash','')
        user.oauth_source = hit["_source"].get('oauth_source','')
        user.included_data_sources = hit["_source"].get("included_data_sources",'')
        user.excluded_data_sources = hit["_source"].get("excluded_data_sources",'')
        return (True, user)    
    else:
        return (False, user)

def update_user_preferences_data_sources(user):
    es_client.update(
        index=ES_Index.users.name, 
        id=user.id,   
        doc={
            "included_data_sources": user.included_data_sources,
            "excluded_data_sources": user.excluded_data_sources,
            "timestamp_updated": datetime.now(timezone.utc),
        }
    )

def get_users(start_date, end_date):
    start_date, end_date = parse_date_range_for_elastic(start_date, end_date)
    # result = es_client.search(index=ES_Index.users.name, query={"match": {"first_name": {"query": "first"}}}, size=100, sort=[{ "timestamp_created" : "asc" }])   
    result = es_client.search(index=ES_Index.users.name, 
                              size=10000,
                              query = {
                                    "range": { 
                                        "timestamp_created": {
                                            "gte":start_date, 
                                            "lte":end_date,
                                        }
                                    }
                                },
                                sort=[{ "timestamp_created" : "desc" }])    
    return result["hits"]["hits"]

def delete_user(user_id:str):
    es_client.delete(index=ES_Index.users.name, id=user_id)

#endregion


#region DECORATORS

from functools import wraps
from time import time
import inspect
import os

def timeit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ts = time()
        result = f(*args, **kwargs)
        te = time()
        filename = os.path.basename(inspect.getfile(f))
        # print('file:%r func:%r took: %2.4f sec' % (filename, f.__name__, te-ts))
        log_event(type="info", filename=filename, method=f.__name__, message=f"execution time: {(te-ts):2.4f} sec")
        return result
    return decorated_function

def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            ts = time()
            result = f(*args, **kwargs)
            te = time()
            filename = os.path.basename(inspect.getfile(f))            
            log_event(type="info", filename=filename, method=f.__name__, message=f"execution time: {(te-ts):2.4f} sec")
            return result
        except Exception as ex:
            filename = os.path.basename(inspect.getfile(f))
            log_event(type="error", filename=filename, method=f.__name__, message=str(ex), traceback= traceback.format_exc())
    return decorated_function

def set_cookies(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # first set the session id
        if request.cookies.get('session') is None:
            session_id = str(uuid.uuid4())
        else:
            session_id = request.cookies['session']        
        session['gateway-session-id'] = session_id

        if current_user.is_authenticated:
            session["current-user-email"] = current_user.email

        response = f(*args, **kwargs)

        log_agent()
        log_activity(f"loading route: {f.__name__}")

        # Set 'nfdi4ds-gateway-search-session' cookie to the session_id
        # response.set_cookie('session', session_id)
        
        return response
    return decorated_function



#endregion