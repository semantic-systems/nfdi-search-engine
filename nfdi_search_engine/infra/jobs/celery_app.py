from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING

from celery import Celery
from celery.signals import task_failure, task_prerun

if TYPE_CHECKING:
    from flask import Flask

log = logging.getLogger(__name__)

# Every module in this package is imported at startup so its @celery_app.task
# functions register themselves. Importing a module does not create a task, only
# the decorator does, so shared helpers may live here as well.
TASK_PACKAGE = "nfdi_search_engine.infra.jobs.tasks"

celery_app = Celery("nfdi")


def _discover_task_modules() -> list[str]:
    """
    Return every module in the task package.
    """
    pkg = importlib.import_module(TASK_PACKAGE)
    return sorted(
        module.name
        for module in pkgutil.walk_packages(pkg.__path__, prefix=f"{TASK_PACKAGE}.")
        if not module.name.rsplit(".", 1)[-1].startswith("_")
    )


def init_celery(flask_app: "Flask") -> Celery:
    """
    Configure the Celery app and register all task modules.

    Tasks are plain module-level functions, so they cannot capture the objects
    built in create_app(). Instead every task runs inside a Flask application
    context and resolves its dependencies from ``current_app.extensions``, the
    same way the web layer does.
    """
    cfg = flask_app.config["CELERY"]
    jobs = flask_app.config["JOBS"]

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask

    modules = _discover_task_modules()

    celery_app.conf.update(
        broker_url=cfg["broker_url"],
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # nothing reads job results, so the result backend is left unset
        task_ignore_result=True,
        worker_prefetch_multiplier=1,
        timezone="UTC",
        enable_utc=True,
        beat_schedule=jobs["beat_schedule"],
        beat_schedule_filename=cfg["beat_schedule_filename"],
        include=modules,
    )

    # import eagerly, so a broken task module fails at startup instead of
    # silently inside the worker thread
    for module in modules:
        importlib.import_module(module)

    log.info(
        "Registered jobs: %s",
        ", ".join(t for t in sorted(celery_app.tasks) if not t.startswith("celery.")),
    )

    flask_app.extensions["celery"] = celery_app
    return celery_app


@task_prerun.connect
def _on_task_start(task_id=None, task=None, **kwargs):
    log.info("Job started: %s (id=%s)", getattr(task, "name", "unknown"), task_id)


@task_failure.connect
def _on_task_failure(task_id=None, exception=None, sender=None, **kwargs):
    log.error(
        "Job failed: %s (id=%s): %r",
        getattr(sender, "name", "unknown"), task_id, exception,
    )
