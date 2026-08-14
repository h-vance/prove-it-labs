#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

KX="kubectl --context kind-proveit -n tse-training"

assert "Deployment has both replicas available" \
    --run "$KX get deployment orders-api -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo none" \
    --equals "2" \
    --expect "availableReplicas 2, meaning the rollout actually completed" \
    --retries 30 --delay 3

# A Service can look perfectly healthy while routing to nothing. Ready endpoints
# are the fact that separates "the Service exists" from "the Service works".
assert "Service has ready endpoints behind it" \
    --run "bash \$TSE_STACK_DIR/endpoints.sh" \
    --equals "2" \
    --expect "2 ready endpoints in the orders-api EndpointSlice" \
    --retries 20 --delay 3

assert "Customer workflow returns orders through the Service" \
    --run "bash \$TSE_STACK_DIR/probe.sh" \
    --contains '"order_count": 3' \
    --expect 'the orders payload served over http://orders-api:8080/customers' \
    --retries 15 --delay 3

finish
