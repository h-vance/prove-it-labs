FROM python:3.12-alpine3.24

RUN addgroup -S app && adduser -S -G app app

WORKDIR /app
COPY api.py /app/api.py

EXPOSE 8080
USER app
CMD ["python", "/app/api.py"]
