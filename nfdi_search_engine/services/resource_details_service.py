from __future__ import annotations

import importlib
import traceback
from typing import Any, Optional

import requests

from nfdi_search_engine.common.models.objects import CreativeWork
from nfdi_search_engine.common.models.details_settings import DetailsSettings
from nfdi_search_engine.services.tracking_service import TrackingService


class ResourceDetailsService:
    """
    Service for all resource-details operations.

    This service contains the orchestration logic for:
    - resource details harvesting
    """

    def __init__(
        self,
        settings: DetailsSettings,
        tracking: TrackingService,
        http: Optional[requests.Session] = None,
    ):
        self.settings = settings
        self.tracking = tracking
        self.http = http

    def get_resource_details(self, doi: str, source_name: str) -> Optional[CreativeWork]:
        """
        Returns resource details for the given doi from the given source.
        Uses the .get_resource() method from the source module.
        """
        try:
            mod_name = self.settings.data_sources[source_name].get(
                "module", ""
            )
            mod = importlib.import_module(f"sources.{mod_name}")
            return mod.get_resource(source_name, source_name, doi, tracking=self.tracking)
        except Exception as e:
            self.tracking.log_event_async(
                log_type="error",
                filename=mod.__file__,
                args=[source_name, source_name, doi],
                method="get_resource",
                message=traceback.format_exception_only(e),
                traceback=traceback.format_exception(e),
            )
