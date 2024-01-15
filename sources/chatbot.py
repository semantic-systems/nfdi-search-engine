import requests

def chat(question, data):
    chat_results = []
    chatbot_url = 'http://0.0.0.0:5005/'
    ping_response = requests.get(chatbot_url + 'ping')
    ping_message = ping_response.text
    print(ping_message)
    body = ''
    # chat_response = requests.get(chatbot_url + 'chat' + body)
    # return chat_results


chat("Hi", "data")
