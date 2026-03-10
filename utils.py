import os
from bs4 import BeautifulSoup
import traceback
import inspect


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
def parse_date(date_str):
    try:
        parsed_date_str = parse(date_str).strftime("%Y-%m-%d")
        return parsed_date_str
    except (TypeError, ValueError):
        print(f"original date str: {date_str}")
        return ""

from elasticsearch import Elasticsearch, exceptions
es_client = Elasticsearch(
    os.environ.get("ELASTIC_SERVER", ""),  # Elasticsearch endpoint
    basic_auth=(os.environ.get("ELASTIC_USERNAME", ""), os.environ.get("ELASTIC_PASSWORD", "")),
    # api_key="aWozWnVKQUItaEJISkZmZS1hd1c6WFQ3OUdZdUlTZFdZUDlqcmVGVkhvdw==",
) 

from enum import Enum
class ES_Index(Enum):
    event_logs_old = 4

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

def log_event(type: str = "info", filename: str = None, method: str = None, args = None, kwargs = None, message: str = None, traceback = None):

    if not filename:
        caller_frame = inspect.stack()[1]
        caller_filename_full = caller_frame.filename
        filename = os.path.splitext(os.path.basename(caller_filename_full))[0]
    
    if not method:
        method = inspect.stack()[1][3]

    es_client.index(
        index=ES_Index.event_logs_old.name,        
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
