from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import requests
import xmltodict
from requests.adapters import HTTPAdapter

from config import Config
from nfdi_search_engine.common.formatting import clean_json


class HttpClient(requests.Session):
    """
    HTTP client for a single source.

    Applies the configured timeout and user agent to every request.
    """

    def __init__(self, timeout: int = None, user_agent: str = None) -> None:
        super().__init__()
        self._timeout = int(timeout if timeout is not None else Config.REQUEST_TIMEOUT)

        # most upstreams only return json when asked; get_text overrides this
        self.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": user_agent or Config.REQUEST_HEADER_USER_AGENT,
        })

        # urllib3 sleeps for Retry-After before raising, which a request timeout
        # does not bound, so one rate-limited source could stall the harvest
        self.mount("http://", HTTPAdapter(max_retries=0))
        self.mount("https://", HTTPAdapter(max_retries=0))

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return super().request(method, url, **kwargs)

    def get_json(self, url: str, **kwargs) -> Any:
        """GET and parse a JSON response, dropping keys without a value."""
        response = self.get(url, **kwargs)
        response.raise_for_status()
        return clean_json(response.json())

    def get_xml(self, url: str, **kwargs) -> Any:
        """GET and parse an XML response into dicts, dropping keys without a value."""
        response = self.get(url, **kwargs)
        response.raise_for_status()
        return clean_json(xmltodict.parse(response.text))

    def get_text(self, url: str, **kwargs) -> str:
        """GET a response that is neither JSON nor XML, e.g. an HTML page."""
        headers = {"Accept": "*/*", **(kwargs.pop("headers", None) or {})}
        response = self.get(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.text


def quote_term(term: str) -> str:
    """Encode a search term or identifier for use in a request URL."""
    return quote_plus(term, safe="()?&=,")
