FROM python:3.9.16-slim-buster

COPY . .

RUN python -m pip install --upgrade pip
RUN pip install psycopg2-binary
RUN pip install -r requirements.txt
