#!/bin/sh
# Issue the lab CA and the three gateway certificates it has signed over time.
#
# Every field that appears in output is fixed: the validity bounds, the serial,
# and the subject. Only the key material is random, so the only thing that moves
# between two builds of this image is the base64 body of the certificate, which
# the recorder folds away. That is what lets a recorded `openssl` command be
# compared byte for byte in CI against a stack built on a different machine.
#
# The three versions tell an ordinary story. v1 covered both names and has
# expired. v2 was issued to replace it and quietly dropped a name. v3 is the
# reissue that puts the name back. Losing a subject alternative name during a
# rotation is one of the most common ways a working service starts failing for
# one caller and nobody else.
set -eu

cd /certs

CA_SUBJECT="/C=US/O=Prove It Lab/CN=Prove It Lab Internal CA"
GATEWAY_SUBJECT="/C=US/O=Prove It Lab/CN=gateway"

openssl req -x509 -newkey rsa:2048 -nodes -sha256 \
    -keyout ca.key -out ca.pem \
    -subj "$CA_SUBJECT" \
    -set_serial 1 \
    -not_before 20250101000000Z -not_after 20351231235959Z \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"

# issue <name> <serial> <not_before> <not_after> <subjectAltName>
issue() {
    name=$1
    serial=$2
    not_before=$3
    not_after=$4
    san=$5

    openssl req -new -newkey rsa:2048 -nodes \
        -keyout "$name.key" -out "$name.csr" \
        -subj "$GATEWAY_SUBJECT"

    openssl x509 -req -in "$name.csr" \
        -CA ca.pem -CAkey ca.key \
        -set_serial "$serial" -sha256 \
        -not_before "$not_before" -not_after "$not_after" \
        -out "$name.crt" \
        -extfile /dev/stdin <<EXTENSIONS
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=$san
EXTENSIONS

    # The gateway loads one file holding both halves, so there is one path in
    # the configuration rather than two that can disagree with each other.
    cat "$name.crt" "$name.key" > "$name.pem"
    rm -f "$name.csr" "$name.crt" "$name.key"
}

issue v1 11 20250101000000Z 20250401000000Z "DNS:gateway,DNS:reports"
issue v2 12 20250401000000Z 20351231235959Z "DNS:gateway"
issue v3 13 20250401000000Z 20351231235959Z "DNS:gateway,DNS:reports"

rm -f ca.key
chmod 0644 /certs/*.pem
