FROM python:3.9.16-slim

COPY . .

RUN pip install -r requirements.txt

