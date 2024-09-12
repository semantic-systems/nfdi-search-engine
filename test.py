import os
from config import Config

from elasticsearch import Elasticsearch, exceptions
es_client = Elasticsearch(
    os.environ.get("ELASTIC_SERVER", ""),  # Elasticsearch endpoint
    basic_auth=(os.environ.get("ELASTIC_USERNAME", ""), os.environ.get("ELASTIC_PASSWORD", "")),
    # api_key="aWozWnVKQUItaEJISkZmZS1hd1c6WFQ3OUdZdUlTZFdZUDlqcmVGVkhvdw==",
) 
# es_client = Elasticsearch(
#     "http://localhost:9200/",  # Elasticsearch endpoint
#     basic_auth=("elastic", "gQyfAiLs-7mQ+Mq8dNCm"),
#     # api_key="aWozWnVKQUItaEJISkZmZS1hd1c6WFQ3OUdZdUlTZFdZUDlqcmVGVkhvdw==",
# ) 
from enum import Enum
class ES_Index(Enum):
    user_activity_log = 1
    users = 2
    event_logs = 3


# es_client.delete(index=ES_Index.users.name, id="a-gMAZEBUmJ85srMM-TI")
# try:
#     result = es_client.get(index=ES_Index.users.name, id="a-gMAZEBUmJ85srMM-TI")
#     print(result)
# except exceptions.NotFoundError:
#     pass


# es_client.delete(index=ES_Index.event_logs.name, id="xpLy4pEBN-GSHUrf3P7M")