from __future__ import annotations
from typing import Any, Dict, Protocol


class JobDispatcher(Protocol):
    def enqueue(self, name: str, payload: Dict[str, Any]) -> None: ...
