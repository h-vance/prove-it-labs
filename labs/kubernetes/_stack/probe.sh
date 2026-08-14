#!/usr/bin/env bash
# Exercises the customer-facing workflow from inside the cluster.
#
# Going through the Service name rather than straight to a Pod is deliberate:
# it proves DNS, the Service, its endpoints, and the application in one call,
# which is exactly the path a real request takes.
set -uo pipefail

NS=tse-training
CTX=kind-proveit
PYTHON_PROBE='import urllib.request,sys
sys.stdout.write(urllib.request.urlopen("http://orders-api:8080/customers", timeout=3).read().decode())'

pod=$(kubectl --context "$CTX" -n "$NS" get pods \
        -l app.kubernetes.io/name=orders-api \
        --field-selector=status.phase=Running \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [[ -z $pod ]]; then
    echo "no running orders-api pod to probe from"
    exit 1
fi

kubectl --context "$CTX" -n "$NS" exec "$pod" -- python -c "$PYTHON_PROBE" 2>&1
