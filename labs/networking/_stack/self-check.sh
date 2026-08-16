#!/usr/bin/env bash
# Assert the client trusts the authority that actually signed the gateway.
#
# This stack builds its own CA, and `issue-certificates.sh` mints fresh RSA
# keys every time it runs. The gateway and the client used to take their
# certificates from that stage in parallel, so a partial rebuild could run it
# twice and hand them two different CAs. Every exercise in the track then fails
# on an unknown issuer, which is not what any of them teach, and the content
# looks like the culprit.
#
# The Dockerfile now chains the stages so that cannot happen. This is the check
# that says so, and it is the only thing standing between a silent recurrence
# and a learner losing an evening.
#
# Public certificates only. No key is read, copied or printed here.
set -uo pipefail

STACK_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
COMPOSE="docker compose -f $STACK_DIR/compose.yaml"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Read from the built images rather than a running stack, so this is about what
# was built and does not need anything to be up.
gateway_image=$($COMPOSE config --images 2>/dev/null | head -1)
if [[ -z $gateway_image ]]; then
    echo "self-check: the networking stack has not been built." >&2
    exit 1
fi

extract() {
    # $1 service, $2 path inside the image, $3 where to put it
    if ! $COMPOSE run --rm --no-deps --entrypoint sh "$1" \
            -c "cat $2" > "$3" 2>/dev/null; then
        echo "self-check: could not read $2 out of the $1 image." >&2
        exit 1
    fi
    if [[ ! -s $3 ]]; then
        echo "self-check: $2 in the $1 image is empty." >&2
        exit 1
    fi
}

extract client /usr/local/share/ca-certificates/proveit-lab-ca.crt "$work/ca.pem"
extract gateway /certs/v3.pem "$work/gateway.pem"

# v3.pem holds the certificate and its key in one file, which is how the
# gateway loads it. Take only the certificate, so no private key is written
# outside the image even briefly.
awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/' \
    "$work/gateway.pem" > "$work/gateway.crt"

# The gateway certificate is deliberately valid until 2035, so this is a
# question about the signature and not about the clock.
if openssl verify -CAfile "$work/ca.pem" "$work/gateway.crt" >/dev/null 2>&1; then
    echo "The client trusts the authority that signed the gateway."
    exit 0
fi

echo "self-check: the client and the gateway hold two different lab CAs." >&2
echo >&2
echo "  The client trusts:" >&2
openssl x509 -in "$work/ca.pem" -noout -subject -fingerprint -sha256 2>&1 | sed 's/^/    /' >&2
echo "  The gateway certificate was signed by:" >&2
openssl x509 -in "$work/gateway.crt" -noout -issuer 2>&1 | sed 's/^/    /' >&2
echo >&2
echo "  Rebuild the stack from scratch:" >&2
echo "    docker compose -f $STACK_DIR/compose.yaml build --no-cache" >&2
exit 1
