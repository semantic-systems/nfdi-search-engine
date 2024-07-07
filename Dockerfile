FROM python:3.11-bullseye

RUN apt update; apt install -y libopenblas-base libopenblas-dev

WORKDIR /app

ADD requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

COPY /informatik2/sems/nfdi/nfdi4ds/gateway/.env .

CMD [ "gunicorn", "-w", "4" , "-b", "0.0.0.0", "main:app" ]

EXPOSE 8000/tcp
