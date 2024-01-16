import requests
import json

def read_data(file_name):
    with open(file_name, "r") as f:
        data = f.read()
    return data


def chat(question, searc_data):
    chat_results = []
    chatbot_url = 'http://0.0.0.0:5005/'
    # ping_response = requests.get(chatbot_url + 'ping')
    # ping_message = ping_response.text
    search_data = read_data('../results3.json')
    # print(search_data)
    body = {
        "question": "who is the coauthor of Ricardo Usbeck?",
        "chat-history": [],
        "search-results": search_data
    }
    params = {'data': body}

    response = requests.post(chatbot_url + 'chat', params=params)
    print(response.status_code)
    print(response.text)
    # chat_response = requests.get(chatbot_url + 'chat' + body)
    # return chat_results


chat("Hi", "data")
