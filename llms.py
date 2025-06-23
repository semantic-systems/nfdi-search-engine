import requests
from requests.auth import HTTPBasicAuth
import json
from openai import OpenAI
from config import Config

openai_api_key = Config.LLMS['openai']['open_api_key']
openai_model = Config.LLMS['openai']['openai_model_version']
client = OpenAI(
  api_key=openai_api_key,
)


def chatgpt(prompt, sys_prompt_string="You are an expert on data analysis."):
    # model = openai_model
    # client = OpenAI()
    # completion = client.chat.completions.create(
    #     model=model,
    #     messages=[
    #         {"role": "user", "content": prompt}
    #     ]
    # )
    # try:
    #     json_response = json.loads(completion.choices[0].message.function_call.arguments)
    #     return json_response
    # except Exception as e:
    #     print(f"An error occurred: {e}")
    #     return ""
    url = Config['LLMS']['openai']['url_chat_completions']
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": sys_prompt_string
            },
            {
                "role": "user",
                "content": f"{prompt}"
            }
        ],
        "temperature": 0.7,
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {openai_api_key}'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    merged_publication = json.loads(
        response_json['choices'][0]['message']['content'].replace("```json", "").replace("```", ""))
    print(merged_publication)


def llama(user_prompt, sys_prompt_string="You are an experienced data analyst."):
    url = Config.LLMS['llama3']['url']
    messages = [
        {"role": "system", "content": sys_prompt_string},
        {"role": "user", "content": user_prompt}]
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_new_tokens": 16384,
        "max_seq_len": 1024,
        "max_gen_len": 512
    }
    response = requests.post(
        url,
        headers={'Content-Type': 'application/json'},
        auth=HTTPBasicAuth(Config.LLMS['llama3']['username'], Config.LLMS['llama3']['password']),
        json=payload
    )
    if response.status_code == 200:
        response_data = response.json()
        # print(f"Response: {response_data}")
        if 'generated_text' in response_data:
            generated_text = json.loads(response_data['generated_text'])
            return generated_text
        else:
            return response_data
    else:
        print(f"Error: {response.status_code}")
        print("Response text:", response.text)
        return None


def chatai_models(prompt):
    api_key = Config.LLMS['chatai']['chatai_api_key']
    base_url = Config.LLMS['chatai']['url']
    model = Config.LLMS['chatai']['model']
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    messages = [{"role":"system","content":"You are a helpful assistant"},
                {"role": "user", "content": prompt}]
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=model
    )
    try:
        result = chat_completion.choices[0].message.content
        return result

    except Exception as e:
        print(f"An error occurred while generating answer: {e}")
        return None
