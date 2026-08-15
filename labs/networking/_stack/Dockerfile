# A small internal CA, a gateway that serves TLS, and the client that calls it.
#
# The certificates are generated here rather than committed. A repository with
# private keys in it teaches the wrong habit even when the keys are worthless,
# and a certificate checked into git is one somebody eventually reuses.

FROM python:3.12-alpine3.24 AS certs

RUN apk add --no-cache openssl

# Fail the build rather than the exercise.
#
# `-not_after` arrived in OpenSSL 3.5. Without it openssl falls back to its
# default validity and mints a certificate that is *valid*, so the expired
# exercise would come up working and look like a content mistake rather than a
# toolchain one. `tse verify` catches that through its fail-broken half, but it
# reports a lab that is not broken, which is a long way from the cause.
#
# The capability is tested rather than the version string, because the version
# is a proxy for the thing that actually matters.
RUN openssl req -x509 -help 2>&1 | grep -q -- '-not_after' || { \
        echo "This openssl cannot set explicit certificate validity bounds."; \
        echo "OpenSSL 3.5 or newer is required. Found: $(openssl version)"; \
        exit 1; \
    }

WORKDIR /certs
COPY issue-certificates.sh /usr/local/bin/issue-certificates.sh
RUN sh /usr/local/bin/issue-certificates.sh


# --------------------------------------------------------------------------- #
# The gateway. Holds the certificates and the keys that go with them.
# --------------------------------------------------------------------------- #
FROM python:3.12-alpine3.24 AS gateway

RUN apk add --no-cache openssl && adduser -S -u 1000 gateway

COPY --from=certs /certs/v1.pem /certs/v2.pem /certs/v3.pem /certs/
COPY gateway.py /app/gateway.py

USER gateway
EXPOSE 8443
CMD ["python", "/app/gateway.py"]


# --------------------------------------------------------------------------- #
# The client. Trusts the lab CA, and holds no key of its own.
#
# This is the customer's nightly integration. Every command in this track runs
# in here rather than on the host, because TLS error wording comes from
# whichever library curl was linked against and the host's is not knowable.
# The api track already paid for that lesson: the same curl failure printed
# exit 52 on one machine and 56 on another.
# --------------------------------------------------------------------------- #
FROM python:3.12-alpine3.24 AS client

RUN apk add --no-cache openssl curl && adduser -S -u 1000 integration

COPY --from=certs /certs/ca.pem /usr/local/share/ca-certificates/proveit-lab-ca.crt
RUN update-ca-certificates

COPY upload.sh /app/upload.sh
RUN chmod 0755 /app/upload.sh

USER integration
CMD ["sleep", "infinity"]
