FROM python:3.12-alpine3.24

RUN adduser -S -u 1000 app

WORKDIR /app
COPY api.py downstream.py traffic.py /app/

USER app
CMD ["python", "/app/api.py"]
