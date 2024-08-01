from elasticsearch import Elasticsearch, exceptions
es_client = Elasticsearch(
    "http://localhost:9200/",  # Elasticsearch endpoint
    basic_auth=("elastic", "gQyfAiLs-7mQ+Mq8dNCm"),
    # api_key="aWozWnVKQUItaEJISkZmZS1hd1c6WFQ3OUdZdUlTZFdZUDlqcmVGVkhvdw==",
) 
from enum import Enum
class ES_Index(Enum):
    user_activity_log = 1
    users = 2


# es_client.delete(index=ES_Index.users.name, id="a-gMAZEBUmJ85srMM-TI")
try:
    result = es_client.get(index=ES_Index.users.name, id="a-gMAZEBUmJ85srMM-TI")
    print(result)
except exceptions.NotFoundError:
    pass

