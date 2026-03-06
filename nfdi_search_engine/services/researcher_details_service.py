from __future__ import annotations

import importlib
from typing import Any, List, Optional, Set, Tuple

import requests

from objects import Author
from nfdi_search_engine.common.details_settings import DetailsSettings
from nfdi_search_engine.common.openai_settings import OpenAISettings
from nfdi_search_engine.util.merge import merge_objects


class ResearcherDetailsService:
    """
    Service for all researcher-details operations.

    This service contains the orchestration logic for:
    - Researcher details page harvesting across sources
    - Researcher object consolidation / merging
    - Researcher 'about me' text generation
    """
    def __init__(
        self,
        settings: DetailsSettings,
        openai: OpenAISettings,
        http: Optional[requests.Session] = None,
    ):
        self.settings = settings
        self.openai = openai
        self.http = http or requests.Session()

    def get_researchers_for_details_page(
        self,
        *,
        orcid: str,
        excluded_sources: Set[str],
    ) -> Tuple[List[Author], List[str]]:
        """
        Harvest researcher records across all enabled data sources for the given ORCID.
        Uses the .get_researcher() method from source modules
        
        :param orcid: The ORCID string
        :type orcid: str
        :param excluded_sources: Sources to ignore
        :type excluded_sources: Set[str]
        :return: researcher author objects, source names that raised an exception
        :rtype: Tuple[List[Author], List[str]]
        """
        orcid = orcid.lower()

        sources: List[str] = []
        for src in self.settings.data_sources:
            cfg = self.settings.data_sources[src]
            if str(cfg.get("get-researcher-endpoint", "")).strip() and src not in excluded_sources:
                sources.append(src)

        def get_researcher(source: str, module_name: str, orcid_: str) -> List[Any]:
            mod = importlib.import_module(f"sources.{module_name}")
            partial: List[Any] = []
            mod.get_researcher(source, orcid_, source, partial)
            return partial

        from concurrent.futures import ThreadPoolExecutor, as_completed

        researchers: List[Any] = []
        failed: List[str] = []

        max_workers = min(self.settings.max_workers, len(sources) or 1)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(get_researcher, src, self.settings.data_sources[src]["module"], orcid): src
                for src in sources
            }
            for fut in as_completed(futures):
                src = futures[fut]
                try:
                    partial = fut.result()
                    researchers.extend(partial or [])
                except Exception:
                    failed.append(src)

        return researchers, failed

    def merge_researchers(self, researchers: List[Any]) -> Any:
        """
        Merge multiple researcher objects into a single researcher representation.
        
        :param researchers: List of researcher-like objects
        :type researchers: List[Any]
        :return: Single object with merged fields
        :rtype: Any
        """
        if not researchers:
            return None
        if len(researchers) == 1:
            return researchers[0]
        return merge_objects(researchers, self.settings.mapping_preference["researchers"])

    def generate_about_me(self, researcher_details_json: dict | str) -> str:
        """
        Generate an 'about me' paragraph based on the provided researcher details using an LLM.
        
        :param researcher_details_json: Information about the researcher in a json format
        :type researcher_details_json: dict | str
        :return: 'about me' paragraph
        :rtype: str
        """
        if not self.openai.url_chat_completions or not self.openai.api_key:
            raise RuntimeError("OpenAI configuration missing")

        system_content = (
            "Generate an introductory paragraph (4-6 sentences) for the researcher whose "
            "affiliation, publications, research interests are provided in the form of key value pairs, "
            "wherein the definitions of the keys are derived from schema.org. "
            "The summary should briefly describe the researcher's current affiliation, highlight notable "
            "publications, and outline their main research interests. "
            "It should not include the researcher ORCID link in the generated summary. "
            "Generate the summary for the information provided, avoid including any external information or knowledge."
        )

        payload = {
            "model": self.openai.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"{researcher_details_json}"},
            ],
            "temperature": self.openai.temperature,
        }

        resp = self.http.post(
            self.openai.url_chat_completions,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai.api_key}",
            },
            json=payload,
            timeout=self.openai.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
