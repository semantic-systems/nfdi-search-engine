import requests
import json
import utils

def load_search_results(file_name):
    with open(file_name, "r", encoding="utf8") as f:
        data = json.load(f)        
    return data



def getAnswer(question, context):
    url = utils.config['chatbot_url']  #"https://nfdi-chatbot.nliwod.org/chat"

    #later remove these two lines
    # question = "You are talking about who?"
    context = load_search_results('results3.json') #later remove this line

    payload = json.dumps({
        # "question": "who is the coauthor of Ricardo Usbeck?",
        "question": question,
        "chat-history": [],
        "search-results": context
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("GET", url, headers=headers, data=payload)    
    json_response = response.json()
    chat_history = json_response['chat-history']
    lastest_response = chat_history[-1]

    print('Question:', lastest_response['input'])
    print('Answer:', lastest_response['output'])

    return lastest_response['output']


