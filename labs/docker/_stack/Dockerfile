# One base tag across every stack in the course, and it names the Alpine
# release rather than leaving it floating. `python:3.12-alpine` and
# `python:3.12-alpine3.24` are the same image today. They stop being the same
# the day Alpine 3.25 ships, and at that point two of the five stacks would
# have moved operating system and three would not.
FROM python:3.12-alpine3.24

RUN apk add --no-cache postgresql16-client \
    && addgroup -S app \
    && adduser -S -G app app

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8080
USER app
CMD ["python", "/app/app.py"]
