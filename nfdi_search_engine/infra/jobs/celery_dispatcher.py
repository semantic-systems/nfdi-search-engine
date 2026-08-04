from __future__ import annotations

import logging
from typing import Any, Dict

from kombu.exceptions import EncodeError

from nfdi_search_engine.infra.jobs.celery_app import celery_app
from nfdi_search_engine.infra.jobs.dispatcher import JobDispatcher

log = logging.getLogger(__name__)


class CeleryDispatcher(JobDispatcher):
    """
    Job dispatcher via Celery.

    Jobs are published to the broker by task name, so callers never import the
    task implementations. See nfdi_search_engine/infra/jobs/tasks/ for the
    registered names.
    """

    def enqueue(self, name: str, payload: Dict[str, Any]) -> None:
        try:
            celery_app.send_task(name, args=[payload])
        except EncodeError:
            # Celery serializes the payload here, in the calling (request) thread.
            # Enqueuing is fire-and-forget, so an unserializable payload must never
            # escape into the request path.
            log.exception("Job payload is not JSON-serializable, dropping job: %s", name)
        except Exception:
            log.exception("Failed to enqueue job: %s", name)
