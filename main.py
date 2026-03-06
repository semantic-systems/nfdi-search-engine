import os
import uuid
import threading
import copy
import requests
import json
import logging
import logging.config
import secrets
from urllib.parse import urlsplit, urlencode, quote
import importlib
import hmac
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
import time
from urllib.parse import quote, unquote

from flask import (
    Flask,
    Response,
    render_template,
    request,
    make_response,
    session,
    jsonify,
    redirect,
    flash,
    url_for,
    abort,
    send_from_directory,
    abort,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from objects import Article

import utils

from nfdi_search_engine.extensions import limiter, login_manager
from app import create_app

app = create_app()
logger = app.extensions["logger"]
utils.log_event(message="TEST")

from typing import Optional

# region ROUTES

@app.route(
    "/researcher-details/<string:source_name>/<string:source_id>/<string:orcid>/<string:ts>",
    methods=["GET"],
)
@limiter.limit("10 per minute")
@utils.timeit
@utils.set_cookies
def researcher_details(source_name, source_id, orcid, ts):
    utils.log_activity(f"loading researcher details page: {orcid}/{source_id}")

    source_name = unquote(source_name.split(":", 1)[1])
    source_id = unquote(source_id.split(":", 1)[1])
    orcid = unquote(orcid.split(":", 1)[1])
    ts = unquote(ts.split(":", 1)[1])

    print(f"{source_name=}")
    print(f"{source_id=}")
    print(f"{orcid=}")
    print(f"{ts=}")

    try:
        timestamp_signature = ts.encode("utf-8") + b"=" * (4 - len(ts) % 4)
        timestamp_signature = base64.urlsafe_b64decode(timestamp_signature).decode(
            "utf-8"
        )
        print(f"{timestamp_signature=}")

        diff = int(time.time()) - int(float(timestamp_signature))
        print(f"{diff=}")

        if diff > 3600:
            abort(404)
    except Exception as ex:
        abort(404)

    researchers = []
    sources = []
    excluded_sources = set()

    if not current_user.is_anonymous:
        excluded_sources = set((current_user.excluded_data_sources or "").split('; '))

    # Load all the sources from config.py used to harvest data related to search term
    for module in app.config["DATA_SOURCES"]:
        if (
            app.config["DATA_SOURCES"][module]
            .get("get-researcher-endpoint", "")
            .strip() != ""
            and module not in excluded_sources
        ):
            sources.append(module)

    def get_researcher(source, module_name, orcid, source_id) -> tuple[Optional[list], Optional[Exception]]:
        mod = importlib.import_module(f"sources.{module_name}")
        partial = []

        try:
            mod.get_researcher(source, orcid, source_id, partial)
            return partial, None
        except Exception as e:
            return None, e

    max_workers = min(16, len(sources) or 1)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(
                get_researcher, 
                source, 
                app.config["DATA_SOURCES"][source]["module"], 
                orcid, 
                source_id
            ): source
            for source in sources
        }
        for fut in as_completed(futures):
            source = futures[fut]
            partial, err = fut.result()
            if err:
                logger.warning("Source failed: %s: %s", source, err)
                continue

            researchers.extend(partial)

    # publications_json = jsonify(publications)
    # with open('publications.json', 'w', encoding='utf-8') as f:
    #     json.dump(jsonify(publications).json, f, ensure_ascii=False, indent=4)

    if len(researchers) == 0:
        # none of our sources found anything about the researcher!
        # show a dummy page for the user
        response = make_response(
            render_template("no-results.html", type="researcher", identifier=orcid)
        )

    elif (
        len(researchers) == 1
    ):  # forward the only publication record received from one of the sources
        response = make_response(
            render_template("researcher-details.html", researcher=researchers[0])
        )
        session["researcher:" + orcid] = researchers[0].model_dump(
            mode="python", exclude_none=True
        )

    else:
        # merge more than one researchers record into one researcher
        merged_researcher = merge_objects(researchers, "researchers")
        response = make_response(
            render_template("researcher-details.html", researcher=merged_researcher)
        )
        session["researcher:" + orcid] = merged_researcher

    return response


@app.route("/generate-researcher-about-me/<string:orcid>", methods=["GET"])
@utils.handle_exceptions
def generate_researcher_about_me(orcid):
    researcher_about_me = generate_researcher_about_me(session["researcher:" + orcid])
    return jsonify(summary=f"{researcher_about_me}")


@app.route(
    "/resource-details/<string:source_name>/<string:source_id>/<string:doi>/<string:ts>",
    methods=["GET"],
)
def resource_details(source_name, source_id, doi, ts):
    source_name = (
        unquote(source_name.split(":", 1)[1])
        if ":" in source_name
        else unquote(source_name)
    )
    source_id = (
        unquote(source_id.split(":", 1)[1]) if ":" in source_id else unquote(source_id)
    )
    doi = unquote(doi.split(":", 1)[1]) if ":" in doi else unquote(doi)
    ts = unquote(ts.split(":", 1)[1]) if ":" in ts else unquote(ts)

    print(f"{source_name=}")
    print(f"{source_id=}")
    print(f"{doi=}")
    print(f"{ts=}")

    try:
        timestamp_signature = ts.encode("utf-8") + b"=" * (4 - len(ts) % 4)
        timestamp_signature = base64.urlsafe_b64decode(timestamp_signature).decode(
            "utf-8"
        )
        print(f"{timestamp_signature=}")

        diff = int(time.time()) - int(float(timestamp_signature))
        print(f"{diff=}")

        if diff > 3600:
            abort(404)
    except Exception as ex:
        abort(404)

    # search for the resource in only the source_name platform
    try:
        module_name = app.config["DATA_SOURCES"][source_name].get("module", "")
        resource = importlib.import_module(f"sources.{module_name}").get_resource(
            source_name, source_id, doi
        )
    except Exception as ex:
        utils.log_event(
            type="error",
            message=(
                "resource_details - failed to load resource: "
                f"source_name={source_name}, source_id={source_id}, doi={doi}, "
                f"error={str(ex)}"
            ),
        )
        return redirect(url_for("public.index"))

    if resource is None:
        utils.log_event(
            type="error",
            message=(
                "resource_details - get_resource returned None: "
                f"source_name={source_name}, source_id={source_id}, doi={doi}"
            ),
        )
        return redirect(url_for("public.index"))

    response = make_response(
        render_template("resource-details.html", resource=resource)
    )

    return response


@app.route("/digital-obj-details/<path:identifier_with_type>", methods=["GET"])
@limiter.limit("10 per minute")
@utils.timeit
@utils.set_cookies
def digital_obj_details(identifier_with_type):
    utils.log_activity(f"loading digital obj details page: {identifier_with_type}")
    identifier_type = identifier_with_type.split(":", 1)[
        0
    ]  # as of now this is hardcoded as 'doi'
    identifier = identifier_with_type.split(":", 1)[1]
    pass


# endregion


# region GEN AI


system_content_for_publications_merging = """
    You are given a list of digital objects. These digital objects have been duplicated multiple times in the list. 
    Your task is to consolidate these objects into a single object, ensuring that all properties or attributes of each digital object are preserved. 
    If a property or attribute has multiple values, please use your best judgement to determine the final value. 
    The consolidated output should be presented as a JSON format.

    Ensure the following:
    - No property or attribute of the digital object is missed out.
    - If multiple values exist for the same property or attribute, decide the final value based on common sense or logic.
    - The consolidated digital object should be in a valid JSON format.
    - Only the properties of the digital objects should be included in the final JSON.
    - If the final decision on any property's value is 'None', replace that with 'null' in the resulting JSON.
    - Your response should only be the consolidated digital object in JSON format, without any additional details or context.

    """


@utils.handle_exceptions
def generate_response_with_local_llm(publications_json):
    url = app.config["LLMS"]["llama3"]["url"]
    llm_username = app.config["LLMS"]["llama3"]["username"]
    llm_password = app.config["LLMS"]["llama3"]["password"]
    payload = json.dumps(
        {
            "messages": [
                {"role": "system", "content": system_content_for_publications_merging},
                {"role": "user", "content": f"{publications_json}"},
            ],
            "temperature": 0.7,
            "top_p": 0.9,
            "max_new_tokens": 16384,
            "max_seq_len": 1024,
            "max_gen_len": 512,
        }
    )
    headers = {"Content-Type": "application/json"}

    response = requests.request(
        "POST", url, auth=(llm_username, llm_password), headers=headers, data=payload
    )
    response_json = json.loads(response.text)
    generated_text = response_json["generated_text"]
    print(generated_text)
    merged_publication = json.loads(generated_text)
    return merged_publication


@utils.handle_exceptions
def generate_response_with_openai(publications_json):
    url = app.config["LLMS"]["openai"]["url_chat_completions"]
    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_content_for_publications_merging},
                {"role": "user", "content": f"{publications_json}"},
            ],
            "temperature": 0.7,
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    merged_publication = json.loads(
        response_json["choices"][0]["message"]["content"]
        .replace("```json", "")
        .replace("```", "")
    )
    print(merged_publication)
    return merged_publication


@utils.handle_exceptions
def generate_researcher_about_me(researcher_details_json):
    # researcher.about = chat_completion.choices[0].message.content.strip()

    url = app.config["LLMS"]["openai"]["url_chat_completions"]
    system_content = """
    Generate an introductory paragraph (4-6 sentences) for the researcher whose affiliation, publications, research interests are provided in the form of key value pairs, 
    wherein the definitions of the keys are derived from schema.org. 
    The summary should briefly describe the researcher’s current affiliation, highlight notable publications, and outline their main research interests.
    It should not include the researcher ORCID link in the generated summary.
    Generate the summary for the information provided, avoid including any external information or knowledge.

    """
    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"{researcher_details_json}"},
            ],
            "temperature": 0.7,
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    response_message = response_json["choices"][0]["message"]["content"]
    print(response_message)
    return response_message


@utils.handle_exceptions
def generate_researcher_banner(researcher_details_json):
    url = app.config["LLMS"]["openai"]["url_images_generations"]
    prompt = """
    Generate an image with following instructions:
    - A researcher is either working in his desk and books on his table are related to his research areas.
    - or the researcher is reading something in the library and the books in the background are related to his research areas.
    - or the researcher is doing something on his laptop and the screen has diagrams or images related to his research areas.
    - Researcher sketch should be gender neutral.
    - Image should have linear gradient which start with dark colors on the right but fades out with very light colors on the left.
    - Research Areas: artificial intelligence, machine learning, knowledge graphs, computer vision, large language models

    """
    payload = json.dumps(
        {
            "model": "dall-e-3",
            "response_format": "b64_json",
            "quality": "standard",
            "n": 1,
            "prompt": prompt,
            # "size": "1296x193",
            # "size": "1792x1024",
            "size": "1024x1024",
            # Include any additional parameters here
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        generated_banner = response.json()["data"][0]["b64_json"]
        return generated_banner
    else:
        utils.log_event(type="error", message=f"{response.text}")
        return ""

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


# endregion

# region MISC


@utils.handle_exceptions
def merge_objects(object_list, object_type):
    """
    This function revieces a list of objects defined in objects.py, and returns a new object with the merged values of the objects in object_list.
    The preference order for merging is defined under MAPPING_PREFERENCE in config.py.
    """

    # the new object we create will have the type of the object in object_list which is furthest down in the inheritance hierarchy
    # => we search for the obj with the longest __mro__
    target_obj = max(object_list, key=lambda x: len(type(x).__mro__))
    target_cls = type(target_obj)
    merged_object = target_cls()

    # sort object_list by mapping preference
    mapping_pref = app.config["MAPPING_PREFERENCE"].get(object_type, {})

    # this function returns the index of the source in the preference list for the field
    # it returns float('inf') if the source is not in the preference list
    def get_preference_index(obj, field_name):
        # get the name of the source of the object
        source_list = getattr(obj, "source", None)
        source = source_list[0] if source_list else None
        source_name = getattr(source, "name", None) if source else None

        # get the preference order for the field
        pref_list = mapping_pref.get(field_name, mapping_pref.get("__default__", []))

        return (
            pref_list.index(source_name) if source_name in pref_list else float("inf")
        )

    # collect all sources that will be used in the merged object
    sources = set()

    # iterate through the sorted objects and choose the first non-empty value for each field in the merged object
    for field in type(merged_object).model_fields.keys():
        # sort the objects by the current field
        # if the field is not found, the objects are sorted with the __default__ list
        sorted_objects = sorted(
            object_list, key=lambda obj: get_preference_index(obj, field)
        )

        # iterate through the sorted objects until one of them contains a non-empty value for the field
        for obj in sorted_objects:
            val = getattr(obj, field, None)

            if val not in (
                None,
                "",
                [],
                {},
            ):  # check if the value is empty or a placeholder
                setattr(merged_object, field, val)

                # add all sources to the merged object
                source_list = set(getattr(obj, "source", []))
                sources.update(source_list)

                break

    # add the sources to the merged object
    merged_object.source = list(sources)

    return merged_object


# endregion

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
