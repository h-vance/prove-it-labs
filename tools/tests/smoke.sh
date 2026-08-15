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
section "Quiz"

# Answers come from a pipe, which is also the reason the quiz is its own
# command: `tse verify` runs check.sh non-interactively in CI, and a check that
# blocked on stdin would hang the matrix rather than fail it.
quiz_answers() { printf '%s\n' "$@" | "$TSE" quiz sql/03; }

ok_contains "quiz asks the first question" "Question 1 of 3" quiz_answers 2 3 4
ok_contains "quiz marks a right answer"    "Correct."       quiz_answers 2 3 4
ok_contains "quiz marks a wrong answer"    "Not quite."     quiz_answers 1 1 1
# A wrong answer has to say what the answer was, or being wrong teaches nothing.
ok_contains "wrong answers reveal the answer" "The answer:" quiz_answers 1 1 1
ok_contains "quiz scores the run"          "3/3"            quiz_answers 2 3 4
fails_cleanly "quiz rejects an unknown exercise" "no exercise matches" "$TSE" quiz no-such-exercise

# --------------------------------------------------------------------------- #
section "Scaffolding"

SCAFFOLD="labs/docker/98-smoke-scaffold"
rm -rf "$SCAFFOLD"
ok_contains "new creates an exercise" "Created" "$TSE" new docker/98-smoke-scaffold

missing=""
for f in meta.yaml ticket.md check.sh solution.md hints/1.md; do
    [[ -f $SCAFFOLD/$f ]] || missing="$missing $f"
done
# Written as if/else rather than `cond && pass || fail`. That idiom runs the
# third branch whenever the second one returns non-zero, and `fail` does return
# non-zero when it is called without a detail line. The placeholder check below
# hit exactly that: with the defect present it printed FAIL and then ok for the
# same assertion and counted both. The suite still failed, so nothing shipped
# broken, but a contradictory report is worst at the one moment somebody is
# reading it.
if [[ -z $missing ]]; then
    pass "scaffold has every required file"
else
    fail "scaffold has every required file" "missing:$missing"
fi

if [[ -x $SCAFFOLD/check.sh ]]; then
    pass "scaffold check.sh is executable"
else
    fail "scaffold check.sh is executable"
fi

ok_contains "scaffold is discoverable" "98-smoke-scaffold" "$TSE" list --track docker
if grep -q '{{TRACK}}' "$SCAFFOLD/meta.yaml"; then
    fail "scaffold placeholders substituted"
else
    pass "scaffold placeholders substituted"
fi
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

    # ----------------------------------------------------------------------- #
    # A borrowed stack. Mixed exercises set stack_source, so their files are
    # written into another track's _stack rather than their own. Nothing
    # exercised that path until this track existed, and the failure it guards
    # against is quiet: files left behind in a directory the exercise does not
    # own, which the next run of that track would then inherit.
    section "Borrowed stack (stack_source)"

    BORROWED=mixed/01-every-check-is-green-and-nothing-works
    "$TSE" start "$BORROWED" >/dev/null 2>&1

    if [[ -f labs/docker/_stack/compose.override.yaml ]]; then
        pass "a mixed exercise provisions into the stack it borrows"
    else
        fail "a mixed exercise provisions into the stack it borrows"
    fi
    if [[ -e labs/mixed/_stack ]]; then
        fail "a borrowed stack creates no directory of its own"
    else
        pass "a borrowed stack creates no directory of its own"
    fi

    "$TSE" stop >/dev/null 2>&1
    if [[ -f labs/docker/_stack/compose.override.yaml ]]; then
        fail "stop cleans up the borrowed stack behind it"
    else
        pass "stop cleans up the borrowed stack behind it"
    fi

    # ----------------------------------------------------------------------- #
    # A stack with no service in it. The communication track is graded on what
    # the learner writes, so `tse start` materializes files and brings nothing
    # up. The failure this guards against is provisioning quietly trying to run
    # compose against a stack that has no compose file and half succeeding.
    section "Stack with nothing to bring up (stack: none)"

    WRITTEN=communication/01-the-update-you-owe-after-an-outage
    "$TSE" start "$WRITTEN" >/dev/null 2>&1

    if [[ -f labs/communication/_stack/evidence.md ]]; then
        pass "a written exercise materializes its evidence"
    else
        fail "a written exercise materializes its evidence"
    fi
    if [[ -f labs/communication/_stack/compose.yaml ]]; then
        fail "a stack with no service has no compose file"
    else
        pass "a stack with no service has no compose file"
    fi

    "$TSE" stop >/dev/null 2>&1
    if [[ -f labs/communication/_stack/evidence.md ]]; then
        fail "stop clears a written exercise behind it"
    else
        pass "stop clears a written exercise behind it"
    fi

    # ----------------------------------------------------------------------- #
    # Every track that owns a stack, brought up and torn down once. Three of
    # these were added after the loop above was written and none of them were
    # covered by anything: a track can be verified exercise by exercise and
    # still have a stack that leaves files behind or refuses to start twice.
    section "Every stack starts and stops"

    for exercise in \
        linux/01-disk-has-space-and-writes-still-fail \
        networking/01-nightly-upload-stopped-and-nothing-changed \
        observability/01-the-dashboard-is-green-and-they-are-timing-out
    do
        track=${exercise%%/*}
        if "$TSE" start "$exercise" >/dev/null 2>&1; then
            pass "$track starts"
        else
            fail "$track starts"
        fi
        "$TSE" stop >/dev/null 2>&1
        if compgen -G "labs/$track/_stack/compose.override.yaml" >/dev/null; then
            fail "$track leaves nothing behind"
        else
            pass "$track leaves nothing behind"
        fi
    done
fi

# --------------------------------------------------------------------------- #
# The assertion library every one of the graders is built on. Its own behavior
# had no test at all, which is how it spent this long reporting "0 of 0 checks
# passed" and exiting 0.
section "Assertion library"

if bash -c "source '$ROOT/tools/lib/assert.sh'; finish" >/dev/null 2>&1; then
    fail "a grader that ran no checks is refused" "it exited 0 having proved nothing"
else
    pass "a grader that ran no checks is refused"
fi

if bash -c "source '$ROOT/tools/lib/assert.sh'
            assert 'a thing that is true' --run 'echo yes' --contains yes
            finish" >/dev/null 2>&1; then
    pass "a grader whose checks pass still passes"
else
    fail "a grader whose checks pass still passes" "the refusal above is too broad"
fi

if bash -c "source '$ROOT/tools/lib/assert.sh'
            assert 'a thing that is not true' --run 'echo yes' --contains no
            finish" >/dev/null 2>&1; then
    fail "a grader whose checks fail still fails"
else
    pass "a grader whose checks fail still fails"
fi

# --------------------------------------------------------------------------- #
# The privacy gate. It runs in CI on every push, and running it here too means
# a scaffolded exercise that pastes in a real path fails before it is committed
# rather than after.
section "Privacy gate"
ok_contains "leak scan runs and reports clean" "clean" "$TSE" leaks

# --------------------------------------------------------------------------- #
[[ -s $STATE_BACKUP ]] && cp "$STATE_BACKUP" "$STATE"
rm -f "$STATE_BACKUP"

printf '\n%d passed, %d failed\n' "$PASSED" "$FAILED"
(( FAILED == 0 )) || exit 1
