from app import create_app
from nfdi_search_engine.infra.jobs.worker import start_worker_threads

app = create_app()

# target for out-of-process celery workers
celery_app = app.extensions["celery"]

# must run at module level: gunicorn loads main:app and skips the __main__ block
start_worker_threads(app)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=True,
        use_reloader=False  # the reloader would run a second beat, which would start every scheduled job twice
    )
