import os
import requests
import json
from main import app

system_content_for_publications_merging = """
    The list contains multiple objects representing the same digital object. Merge these objects into object considering the following rules: 
    - no property should be skipped. 
    - common sense should prevail in case multiple values exist for one property. 
    - final output must be in the json foramt.
    - final output should only contain properties of the digital object. 
    - properties where the merged value is decided to be 'None', should be replaced with null.
    - Please revise… Only reply with the formatted json, nothing else.

    """

def generate_response_with_local_llm(publications_json):

    url = app.config['LLMS']['llama3']['url']
    llm_username = app.config['LLMS']['llama3']['username']
    llm_password = app.config['LLMS']['llama3']['password']
    payload = json.dumps({
        "messages": [
            {
                "role": "system", 
                "content": system_content_for_publications_merging
            },
            {
                "role": "user", 
                "content": f"{publications_json}"
            }
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_new_tokens": 16384,
        "max_seq_len": 1024,
        "max_gen_len": 512
    })
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, auth=(llm_username, llm_password), headers=headers, data=payload)
    response_json = json.loads(response.text)
    generated_text = response_json['generated_text']
    print(generated_text)
    merged_publication = json.loads(generated_text)
    return merged_publication


def generate_response_with_openai(publications_json):
    url = app.config['LLMS']['openai']['url']
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system", 
                "content": system_content_for_publications_merging
            },
            {
                "role": "user", 
                "content": f"{publications_json}"
            }
        ],
        "temperature": 0.7,
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.environ.get("OPENAI_API_KEY", "")}'
    }

    response = requests.request("POST", url, headers=headers, data=payload)    
    response_json = json.loads(response.text)
    merged_publication = json.loads(response_json['choices'][0]['message']['content'].replace("```json","").replace("```",""))    
    print(merged_publication)
    return merged_publication



