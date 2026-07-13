from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=True,
        use_reloader=False  # the reloader would start a second celery beat, which would start every scheduled job twice
    )
