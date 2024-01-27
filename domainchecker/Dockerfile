FROM tiangolo/uvicorn-gunicorn:python3.11

COPY ./app/DomainChecker/requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

COPY ./app/DomainChecker /app
