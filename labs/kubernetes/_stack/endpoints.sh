#!/usr/bin/env bash
# Prints how many endpoints behind the orders-api Service are ready.
#
# A Service with no ready endpoints is the single most useful fact in a
# "reachable but returns nothing" investigation, and it is invisible from the
# Service object alone.
set -uo pipefail

kubectl --context kind-proveit -n tse-training get endpointslices \
    -l kubernetes.io/service-name=orders-api \
    -o jsonpath='{range .items[*]}{range .endpoints[*]}{.conditions.ready}{"\n"}{end}{end}' 2>/dev/null \
    | grep -c '^true$' || true
