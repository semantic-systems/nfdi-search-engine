FROM python:3.10-alpine

WORKDIR /app

ADD requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD [ "flask", "--app", "api", "run"]

CMD [ "python", "main.py" ]

EXPOSE 7860f