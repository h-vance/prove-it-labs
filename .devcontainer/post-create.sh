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
# The linter is here for contributors rather than for learners. CI checks every
# shell script in the repository, and somebody working in a Codespace should be
# able to run that check before pushing rather than after.
#
# Not written as "# shellcheck is ..." because a comment opening with that word
# is read as a directive to the tool itself, which is an error. The stricter
# severity added in the same change caught it immediately.
sudo apt-get install -y -qq jq postgresql-client dnsutils netcat-openbsd shellcheck >/dev/null

chmod +x tools/tse
chmod +x labs/*/*/check.sh 2>/dev/null || true

# Every base image any stack builds on. This list is checked against the
# Dockerfiles by test_content.py, because a pre-pull that misses one is worse
# than no pre-pull: it looks like the wait was handled and two tracks still
# stop to download on first use.
echo "Pre-pulling lab images ..."
docker pull -q postgres:16-alpine &
docker pull -q python:3.12-alpine3.24 &
wait

echo
echo "Checking the environment ..."
# `|| true` used to be the whole story here, which meant a container that came
# up unable to run a single exercise still finished with "Prove It is ready."
# The intent was only that a failed check should not abandon the build halfway,
# leaving a half configured container behind. It still does not, but it now
# says so loudly and the banner tells the truth about which case this is.
if tools/tse doctor; then
    ready=1
else
    ready=0
    echo
    echo "  tse doctor failed. The container is built, and the labs will not run"
    echo "  until the problems above are fixed. Re-run \`tse doctor\` after each"
    echo "  change to see what is left."
fi

if [ "$ready" -eq 1 ]; then
    cat <<'BANNER'

  Prove It is ready.

    tse list                 see every exercise
    tse start docker/01      pick up your first ticket

BANNER
fi
