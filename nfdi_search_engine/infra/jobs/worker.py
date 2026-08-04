from __future__ import annotations

import threading

from flask import Flask

WORKER_THREAD_NAME = "celery-worker"


def start_worker_threads(app: Flask) -> None:
    """
    Run the celery worker and beat as threads inside this process.

    Does nothing when the broker is a real one (see Config.CELERY), or when the
    threads are already running.
    """
    if not app.config["CELERY"]["run_worker_in_process"]:
        return
    if any(t.name == WORKER_THREAD_NAME for t in threading.enumerate()):
        return

    celery_app = app.extensions["celery"]

    # pool="solo", concurrency=1 runs jobs one at a time, in the order they were queued
    threading.Thread(
        target=lambda: celery_app.Worker(
            loglevel="WARNING", pool="solo", concurrency=1, quiet=True
        ).start(),
        daemon=True,
        name=WORKER_THREAD_NAME,
    ).start()
    threading.Thread(
        target=lambda: celery_app.Beat(loglevel="WARNING", quiet=True).run(),
        daemon=True,
        name="celery-beat",
    ).start()
