import re
import time
import base64

from flask import url_for
from urllib.parse import quote, unquote


def quote_filter(x) -> str:
    return quote(str(x), safe="")


def url_encode(value: str | bytes | None) -> str:
    if not value:
        return ""
    # ensure str for quote()
    if isinstance(value, bytes):
        value = value.decode()
    encoded = quote(str(value), safe="")  # '/' -> %2F, space -> %20, ...
    return encoded.replace("%2F", "%252F")  # double-encode slash


def format_digital_obj_url(obj, *fields) -> str:
    """
    Jinja usage examples
        {{ resource | format_digital_obj_url('identifier', 'source_id') }}
        {{ resource | format_digital_obj_url(['identifier', 'source_id']) }}
    """

    # accept either *fields or a single iterable
    if len(fields) == 1 and isinstance(fields[0], (list, tuple)):
        fields = fields[0]

    # implement special cases here
    def _get(field: str) -> str | None:
        match field:
            case "source-id":
                # if a source identifier is available, use it, otherwise 'na'
                if getattr(obj, "source", "") and getattr(
                    obj.source[0], "identifier", ""
                ):
                    val = obj.source[0].identifier
                else:
                    val = "na"
            case "source-name":
                val = obj.source[0].name if getattr(
                    obj, "source", "") else "na"
            case "doi" | "orcid":
                val = obj.identifier if getattr(
                    obj, "identifier", "") else "na"
            case _:
                val = getattr(obj, field, "")
        # print(f"{field=}, {val=}")
        return val

    parts = [f"{f}:{url_encode(_get(f))}" for f in fields if _get(f)]

    current_timestamp = str(time.time())
    timestamp_signature = (
        base64.urlsafe_b64encode(current_timestamp.encode())
        .rstrip(b"=")
        .decode("utf-8")
    )
    parts.append(f"ts:{timestamp_signature}")

    return "/".join(parts)


def get_researcher_url(person, external=True) -> str:
    """
    Jinja usage example
        {{ person | get_researcher_url }}
    """

    if getattr(person, "additionalType", "").lower() != "person":
        return ""
    if not getattr(person, "identifier", None):
        return ""
    orcid_id = str(person.identifier).split("/")[-1]

    if (
        getattr(person, "source", None)
        and person.source
        and getattr(person.source[0], "identifier", None)
    ):
        src_name = person.source[0].name
        src_id = person.source[0].identifier
    else:
        src_name = "na"  # source name is 'na' if not available
        src_id = orcid_id

    current_timestamp = str(time.time())
    timestamp_signature = (
        base64.urlsafe_b64encode(current_timestamp.encode())
        .rstrip(b"=")
        .decode("utf-8")
    )

    return url_for(
        "researcher_details",
        source_name=f"source-name:{url_encode(src_name)}",
        source_id=f"source-id:{url_encode(src_id)}",
        orcid=f"orcid:{url_encode(orcid_id)}",
        ts=f"ts:{url_encode(timestamp_signature)}",
        _external=external,
    )


def format_authors_for_citations(value):
    authors = ""
    for author in value:
        authors += author.name + " and "
    return authors.rstrip(" and ") + "."

def regex_replace(s, find, replace):
    """A less non-optimal implementation of a regex filter"""
    if s is None:
        s_str = ""
    elif isinstance(s, (bytes, bytearray)):
        s_str = s.decode("utf-8", errors="replace")
    else:
        s_str = str(s)

    try:
        out = re.sub(find, replace, s_str)
    except re.error:
        out = s_str

    return out

def register_filters(app) -> None:
    """Register all Jinja filters on a Flask app instance."""
    app.add_template_filter(quote_filter, name="quote")
    app.add_template_filter(
        get_researcher_url,
        name="get_researcher_url"
    )
    app.add_template_filter(
        format_digital_obj_url,
        name="format_digital_obj_url"
    )
    app.add_template_filter(
        format_authors_for_citations,
        name="format_authors_for_citations"
    )
    app.add_template_filter(url_encode, name="url_encode")
    app.add_template_filter(regex_replace, name="regex_replace")
