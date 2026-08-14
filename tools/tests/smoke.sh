#!/usr/bin/env bash
# End-to-end smoke test for the tse CLI.
#
# Covers the command surface, the error paths, and the full learner loop. The
# loop section needs Docker and is skipped without it, so this stays useful as
# a fast check on a machine that cannot run the labs.
#
#   tools/tests/smoke.sh            run everything available
#   tools/tests/smoke.sh --fast     skip the Docker-dependent loop

set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT" || exit 1
TSE="$ROOT/tools/tse"

PASSED=0
FAILED=0
FAST=${1:-}

pass() { PASSED=$((PASSED + 1)); printf '  ok    %s\n' "$1"; }
fail() { FAILED=$((FAILED + 1)); printf '  FAIL  %s\n' "$1"; [[ -n ${2:-} ]] && printf '        %s\n' "$2"; }

# Assert a command succeeds and its output contains a string.
ok_contains() {
    local label=$1 needle=$2; shift 2
    local output status
    output=$("$@" 2>&1); status=$?
    if (( status != 0 )); then
        fail "$label" "exited $status: $(head -2 <<<"$output")"
    elif [[ $output != *"$needle"* ]]; then
        fail "$label" "missing '$needle' in: $(head -2 <<<"$output")"
    else
        pass "$label"
    fi
}

# Assert a command fails and explains itself rather than dumping a traceback.
fails_cleanly() {
    local label=$1 needle=$2; shift 2
    local output status
    output=$("$@" 2>&1); status=$?
    if (( status == 0 )); then
        fail "$label" "expected a non-zero exit"
    elif [[ $output == *"Traceback"* ]]; then
        fail "$label" "raised a traceback instead of an error message"
    elif [[ $output != *"$needle"* ]]; then
        fail "$label" "missing '$needle' in: $(head -2 <<<"$output")"
    else
        pass "$label"
    fi
}

section() { printf '\n%s\n' "$1"; }

# --------------------------------------------------------------------------- #
section "Runs without dependencies"

ok_contains "runs on a stock interpreter" "docker" "$TSE" list
if python3 -c 'import yaml' 2>/dev/null; then
    printf '  note  PyYAML is installed here, so the fallback parser is not exercised\n'
fi

# --------------------------------------------------------------------------- #
section "Discovery"

ok_contains "list shows tracks"        "docker/01" "$TSE" list
ok_contains "list --track filters"     "docker/01" "$TSE" list --track docker
ok_contains "list --ids emits JSON"    "docker/01" "$TSE" list --ids

if "$TSE" list --ids | python3 -c 'import json,sys; d=json.load(sys.stdin); assert isinstance(d,list) and d' 2>/dev/null; then
    pass "list --ids is a non-empty JSON array"
else
    fail "list --ids is a non-empty JSON array"
fi

# Deliberately a name no track will ever have. Naming a real-but-empty track
# here would turn building that track into a failing test.
if [[ -z $("$TSE" list --track no-such-track --ids | tr -d '[]') ]]; then
    pass "list --track handles a track with no exercises"
else
    fail "list --track handles a track with no exercises"
fi

# --------------------------------------------------------------------------- #
section "Exercise resolution"

# Positive resolution is asserted in test_content.py, which can call resolve()
# directly. Here we only cover the failure paths, which are what a learner hits.
fails_cleanly "rejects an unknown id"  "no exercise matches" "$TSE" verify nonexistent/99
fails_cleanly "reports ambiguity"      "ambiguous"           "$TSE" verify "docker/0"
fails_cleanly "unknown subcommand"     "invalid choice"      "$TSE" nonsense

# --------------------------------------------------------------------------- #
section "State errors are explained, not crashed"

STATE="$ROOT/.tse-state.json"
STATE_BACKUP=$(mktemp)
[[ -f $STATE ]] && cp "$STATE" "$STATE_BACKUP"
rm -f "$STATE"

fails_cleanly "check without an active exercise"  "no active exercise" "$TSE" check
fails_cleanly "hint without an active exercise"   "no active exercise" "$TSE" hint
fails_cleanly "answer without an active exercise" "no active exercise" "$TSE" answer
fails_cleanly "apply without an active exercise"  "no active exercise" "$TSE" apply

printf 'not json at all' > "$STATE"
ok_contains "recovers from a corrupt state file" "docker/01" "$TSE" list
rm -f "$STATE"

# --------------------------------------------------------------------------- #
section "Progress and environment"

ok_contains "progress renders"       "overall"  "$TSE" progress
ok_contains "progress --json emits"  "by_track" "$TSE" progress --json
if "$TSE" progress --json | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null; then
    pass "progress --json is valid JSON"
else
    fail "progress --json is valid JSON"
fi
ok_contains "doctor reports on docker" "docker" "$TSE" doctor

# --------------------------------------------------------------------------- #
section "Scaffolding"

SCAFFOLD="labs/docker/98-smoke-scaffold"
rm -rf "$SCAFFOLD"
ok_contains "new creates an exercise" "Created" "$TSE" new docker/98-smoke-scaffold

missing=""
for f in meta.yaml ticket.md check.sh solution.md hints/1.md; do
    [[ -f $SCAFFOLD/$f ]] || missing="$missing $f"
done
[[ -z $missing ]] && pass "scaffold has every required file" \
                  || fail "scaffold has every required file" "missing:$missing"

[[ -x $SCAFFOLD/check.sh ]] && pass "scaffold check.sh is executable" \
                            || fail "scaffold check.sh is executable"

ok_contains "scaffold is discoverable" "98-smoke-scaffold" "$TSE" list --track docker
grep -q '{{TRACK}}' "$SCAFFOLD/meta.yaml" && fail "scaffold placeholders substituted" \
                                          || pass "scaffold placeholders substituted"
fails_cleanly "new refuses to overwrite" "already exists" "$TSE" new docker/98-smoke-scaffold
fails_cleanly "new rejects a bad name"   "expected"       "$TSE" new nosuchformat
rm -rf "$SCAFFOLD"

# --------------------------------------------------------------------------- #
if [[ $FAST == "--fast" ]]; then
    printf '\nSkipping the learner loop (--fast).\n'
elif ! docker info >/dev/null 2>&1; then
    printf '\nSkipping the learner loop (Docker unavailable).\n'
else
    section "Full learner loop"

    EXERCISE=docker/01-service-unavailable-after-deploy
    "$TSE" start "$EXERCISE" >/dev/null 2>&1

    ok_contains "ticket reprints"          "CUSTOMER TICKET" "$TSE" ticket
    ok_contains "hint 1 is a nudge"        "Hint 1 of 3"     "$TSE" hint
    ok_contains "hint 2 escalates"         "Hint 2 of 3"     "$TSE" hint
    ok_contains "hint 3 gives commands"    "Hint 3 of 3"     "$TSE" hint
    ok_contains "hints stop at the end"    "All 3 hints"     "$TSE" hint
    ok_contains "answer reveals the cause" "Root cause"      "$TSE" answer

    if "$TSE" check >/dev/null 2>&1; then
        fail "check fails while the system is broken"
    else
        pass "check fails while the system is broken"
    fi

    # Solve it the way a learner would: edit the config, then apply.
    cp "labs/docker/01-service-unavailable-after-deploy/solution/compose.override.yaml" \
       "labs/docker/_stack/compose.override.yaml"
    "$TSE" apply >/dev/null 2>&1

    if "$TSE" check >/dev/null 2>&1; then
        pass "check passes once the system is fixed"
    else
        fail "check passes once the system is fixed"
    fi

    ok_contains "completion is recorded" "$EXERCISE" "$TSE" progress --json

    "$TSE" reset >/dev/null 2>&1
    if "$TSE" check >/dev/null 2>&1; then
        fail "reset returns to the broken state"
    else
        pass "reset returns to the broken state"
    fi

    ok_contains "stop tears down" "Stopped" "$TSE" stop
    if [[ -f labs/docker/_stack/compose.override.yaml ]]; then
        fail "stop removes the generated override"
    else
        pass "stop removes the generated override"
    fi
fi

# --------------------------------------------------------------------------- #
[[ -s $STATE_BACKUP ]] && cp "$STATE_BACKUP" "$STATE"
rm -f "$STATE_BACKUP"

printf '\n%d passed, %d failed\n' "$PASSED" "$FAILED"
(( FAILED == 0 )) || exit 1
