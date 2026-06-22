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
        mod = None
        try:
            source_cfg = self.settings.data_sources.get(source_name)
            if not source_cfg:
                self.tracking.log_event_async(
                    log_type="warning",
                    method="get_resource_details",
                    args=[source_name, doi],
                    message=f"resource source not configured: {source_name}",
                )
                return None

            mod_name = source_cfg.get(
                "module", ""
            )
            mod = importlib.import_module(f"sources.{mod_name}")
            if not hasattr(mod, "get_resource"):
                self.tracking.log_event_async(
                    log_type="warning",
                    filename=getattr(mod, "__file__", mod_name),
                    method="get_resource_details",
                    args=[source_name, doi],
                    message=f"resource details not supported for source: {source_name}",
                )
                return None
            return mod.get_resource(doi, tracking=self.tracking)
        except Exception as e:
            self.tracking.log_event_async(
                log_type="error",
                filename=getattr(mod, "__file__", source_name),
                args=[source_name, doi],
                method="get_resource",
                message=traceback.format_exception_only(e),
                traceback=traceback.format_exception(e),
            )
