from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable, Dict, Tuple

from nfdi_search_engine.infra.jobs.dispatcher import JobDispatcher

log = logging.getLogger(__name__)


class InProcessDispatcher(JobDispatcher):
    """
    In-process background queue
    """

    def __init__(self, handlers: Dict[str, Callable[[Dict[str, Any]], None]]) -> None:
        self._handlers = handlers
        self._q: "queue.Queue[Tuple[str, Dict[str, Any]]]" = queue.Queue()

        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def enqueue(self, name: str, payload: Dict[str, Any]) -> None:
        self._q.put((name, payload))

    def _run(self) -> None:
        while True:
            name, payload = self._q.get()
            try:
                handler = self._handlers.get(name)
                if handler is None:
                    log.warning("No handler registered for job %r", name)
                else:
                    handler(payload)
            except Exception:
                log.exception("Job failed: %s", name)
            finally:
                self._q.task_done()
