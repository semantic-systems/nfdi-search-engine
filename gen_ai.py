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
    url = app.config['LLMS']['openai']['url_chat_completions']
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

def generate_researcher_about_me(researcher_details_json):    
    
    # researcher.about = chat_completion.choices[0].message.content.strip()

    url = app.config['LLMS']['openai']['url_chat_completions']
    system_content = """
    Generate an introductory paragraph (4-6 sentences) for the researcher whose affiliation, publications, research interests are provided in the form of key value pairs, 
    wherein the definitions of the keys are derived from schema.org. 
    The summary should briefly describe the researcher’s current affiliation, highlight notable publications, and outline their main research interests.
    Generate the summary for the information provided, avoid including any external information or knowledge.

    """
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system", 
                "content": system_content
            },
            {
                "role": "user", 
                "content": f"{researcher_details_json}"
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
    response_message = response_json['choices'][0]['message']['content']  
    print(response_message)
    return response_message

def generate_researcher_banner(researcher_details_json):

    url = app.config['LLMS']['openai']['url_images_generations']
    prompt = """
    Generate an image with following instructions:
    - A researcher is either working in his desk and books on his table are related to his research areas.
    - or the researcher is reading something in the library and the books in the background are related to his research areas.
    - or the researcher is doing something on his laptop and the screen has diagrams or images related to his research areas.
    - Researcher can be male or female.
    - Image should have linear gradient which start with dark colors on the right but fades out with very light colors on the left.
    - Research Areas: artificial intelligence, machine learning, knowledge graphs, computer vision, large language models

    """
    payload = json.dumps({
        "model": "dall-e-3",
        "response_format": "b64_json",
        "quality": "standard",
        "n": 1,
        "prompt": prompt,
        # "size": "1296x193",
        "size": "1792x1024",
        # Include any additional parameters here        
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.environ.get("OPENAI_API_KEY", "")}'
    }

    response = requests.request("POST", url, headers=headers, data=payload)  
    generated_banner = response.json()['data'][0]['b64_json']
    return generated_banner


    # details = vars(researcher)
    # details_str = "\n".join(f"{convert_to_string(value)}" for key, value in details.items() if (value not in ("", [], {}, None) and key in ("researchAreas")))
    # prompt = f"A banner for researcher with following research areas:\n{researcher.about}"
    # client = OpenAI(api_key=utils.env_config["OPENAI_API_KEY"])
    # response = client.images.generate(
    #     model="dall-e-2",
    #     prompt=prompt,
    #     size="512x512",
    #     quality="standard",
    #     response_format="b64_json",
    #     n=1,
    # )
    # researcher.banner = response.data[0].b64_json
    # return researcher
