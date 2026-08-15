#!/usr/bin/env bash
# Grades the exercise by gathering the same evidence a support engineer would.
source "$TSE_LIB/assert.sh"

METRICS="http://127.0.0.1:8102/metrics"
REPORTS="http://127.0.0.1:8102/v1/reports"

# Retries rather than a separate wait, because the sample workload takes a few
# seconds to finish and this assertion is only true once it has. In the broken
# state it never becomes true, and TSE_MAX_RETRIES caps the wait during verify.
assert "This customer's requests meet the objective like everybody else's" \
    --run "curl -s '$METRICS?tenant=northwind' | jq -c '{requests, slow_requests}'" \
    --equals '{"requests":5,"slow_requests":0}' \
    --expect "five requests for this account and none of them over the one second objective" \
    --retries 25 --delay 2

# The fast wrong answer is to give them a configuration that resolves locally
# and is not theirs. It fixes the latency completely and silently gives an
# enterprise account somebody else's limits, which is worse than being slow.
assert "And they get their own configuration, not a fast approximation of it" \
    --run "curl -s '$REPORTS?tenant=northwind' | jq -c '{plan, row_limit}'" \
    --equals '{"plan":"enterprise","row_limit":50000}' \
    --expect "the enterprise plan and a 50000 row limit, which is what the directory holds for them"

finish
