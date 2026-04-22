# sources/base.py
from __future__ import annotations

import os
import inspect
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterable, Dict, Any

if TYPE_CHECKING:
    from nfdi_search_engine.services.tracking_service import TrackingService


class BaseSource(ABC):
    def __init__(self, tracking: TrackingService = None):
        self.tracking = tracking

    def log_event(self, type: str, message: str):
        """
        Match the log_event signature used in sources.
        Async logging to elastic if TrackingService is passed in the constructor,
        to stdout otherwise.
        """
        caller = inspect.stack()[1]
        filename = os.path.splitext(os.path.basename(caller.filename))[0]
        method = inspect.stack()[1][3]

        if self.tracking is not None:
            self.tracking.log_event_async(
                log_type=type,
                message=message,
                filename=filename,
                method=method
            )
        else:
            # if no tracking service is passed, log to stdout
            print(f"{type.upper()}: {filename} in {method}: {message}")

    @abstractmethod
    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        ...

    @abstractmethod
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response. Should return an iterable of hit dicts.
        """
        ...

    @abstractmethod
    def map_hit(self, hit: Dict[str, Any]):
        """
        Map a single hit dict from the source to a object from objects.py (e.g., Article, CreativeWork).
        """
        ...

    @abstractmethod
    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them in-place into the results dict.
        """
        ...
