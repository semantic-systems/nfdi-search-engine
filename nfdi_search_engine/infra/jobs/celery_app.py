import logging

from celery import Celery
from celery.signals import task_prerun

log = logging.getLogger(__name__)

celery_app = Celery(
    "nfdi",
    broker="memory://",
    backend="cache+memory://",
)

# print a log message whenever a task starts
@task_prerun.connect
def _on_task_start(task_id, task, *args, **kwargs):
    log.info("Job started: %s (id=%s)", task.name, task_id)