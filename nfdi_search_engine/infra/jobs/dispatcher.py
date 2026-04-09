from __future__ import annotations
from typing import Any, Dict, Protocol


class JobDispatcher(Protocol):
    """
    Job Dispatcher, implements functions to enqueue background jobs
    """
    def enqueue(self, name: str, payload: Dict[str, Any]) -> None: ...
