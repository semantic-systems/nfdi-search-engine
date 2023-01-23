FROM python:3.11-bullseye

RUN apt update; apt install -y libopenblas-base libopenblas-dev

WORKDIR /app

ADD requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "main" ]


EXPOSE 7860/tcp
