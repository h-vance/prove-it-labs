FROM python:3.12-alpine

RUN apk add --no-cache postgresql16-client \
    && addgroup -S app \
    && adduser -S -G app app

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8080
USER app
CMD ["python", "/app/app.py"]
