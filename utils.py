import os
from bs4 import BeautifulSoup
import traceback
import inspect


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
            raise ex
    return decorated_function
