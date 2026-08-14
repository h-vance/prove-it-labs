#!/usr/bin/env bash
# Prepare the container so the first exercise starts without a download wait.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

echo "Installing kind ..."
if ! command -v kind >/dev/null 2>&1; then
    KIND_VERSION=v0.30.0
    ARCH=$(dpkg --print-architecture)
    curl -fsSLo /tmp/kind \
        "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-${ARCH}"
    sudo install -m 0755 /tmp/kind /usr/local/bin/kind
    rm -f /tmp/kind
fi

echo "Installing lab utilities ..."
sudo apt-get update -qq
sudo apt-get install -y -qq jq postgresql-client dnsutils netcat-openbsd >/dev/null

chmod +x tools/tse
chmod +x labs/*/*/check.sh 2>/dev/null || true

echo "Pre-pulling lab images ..."
docker pull -q postgres:16-alpine &
docker pull -q python:3.12-alpine &
wait

echo
echo "Checking the environment ..."
tools/tse doctor || true

cat <<'BANNER'

  Prove It is ready.

    tse list                 see every exercise
    tse start docker/01      pick up your first ticket

BANNER
