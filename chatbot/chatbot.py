import requests
import json
import utils

def load_search_results(file_name):
    with open(file_name, "r", encoding="utf8") as f:
        data = json.load(f)        
    return data



def getAnswer(question, search_uuid):
    chatbot_server = utils.config['chatbot_server'] 
    chat_endpoint = utils.config['chat_endpoint'] 
    request_url = f"{chatbot_server}{chat_endpoint}"

    #later remove these two lines
    # question = "You are talking about who?"
    # context = load_search_results('results3.json') #later remove this line

    # payload = json.dumps({
    #     # "question": "who is the coauthor of Ricardo Usbeck?",
    #     "question": question,
    #     "chat-history": [],
    #     "search-results": context
    # })

    print('question:', question)
    print('uuid:', search_uuid)

    payload = json.dumps({
        "question": question,
        "search_uuid": search_uuid
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("GET", request_url, headers=headers, data=payload)    
    json_response = response.json()

    response_exception = json_response.get('exception', "")
    response_traceback= json_response.get('traceback', "")

    print('response_exception:', response_exception)
    print('response_traceback:', response_traceback)

    if response_exception == "":
        chat_history = json_response['chat-history']
        lastest_response = chat_history[-1]

        print('Question:', lastest_response['input'])
        print('Answer:', lastest_response['output'])
    else:
        return response_exception

    return lastest_response['output']


