FROM python:3.12-alpine

# Every id is pinned so the exercises can talk about them by number, and so
# `id` inside the container says the same thing on every machine.
#
# app is deliberately a member of reporting. That membership is what
# linux/02 is about: it survives the image's own USER directive and does not
# survive being restated in Compose.
RUN addgroup -g 2000 reporting \
    && addgroup -g 1000 app \
    && adduser -S -u 1000 -G app app \
    && addgroup app reporting \
    && mkdir -p /etc/reporting \
    && printf 'endpoint=https://reports.example.invalid/v1/submit\ntoken=rp_live_synthetic_9f21\n' \
       > /etc/reporting/credentials.conf \
    && chown root:reporting /etc/reporting/credentials.conf \
    && chmod 0640 /etc/reporting/credentials.conf

WORKDIR /app
COPY exporter.py reporter.py /app/

USER app

# The export runs once on the way up so the state described in the ticket is
# already there, then the container stays alive to be investigated. The `;`
# rather than `&&` is deliberate: a failed export must not stop the container,
# or there would be nothing left to look at.
CMD ["sh", "-c", "python /app/exporter.py; sleep infinity"]
