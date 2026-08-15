#!/usr/bin/env bash
# Assertion helpers for exercise check.sh scripts.
#
# The point of this library is that a check never just says pass or fail. It
# shows the assertion, the command it ran, and the raw output it evaluated, so
# the grader teaches evidence gathering instead of hiding it.
#
# Usage inside an exercise check.sh:
#
#   source "$TSE_LIB/assert.sh"
#
#   assert "Application responds on the customer path" \
#       --run 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8100/customers' \
#       --equals '200' \
#       --expect 'HTTP 200 from the customer endpoint' \
#       --retries 20
#
#   finish

set -uo pipefail

_TSE_PASSED=0
_TSE_FAILED=0
_TSE_MAX_OUTPUT_LINES=${TSE_MAX_OUTPUT_LINES:-12}

# GNU coreutils calls it `timeout`; Homebrew's coreutils installs it as
# `gtimeout` unless the user asked for unprefixed names. Looked up once here
# rather than per assertion. If neither exists the assertion runs unbounded,
# which is what it did before this, so nothing is worse off for the lookup
# failing.
_TSE_TIMEOUT_BIN=$(command -v timeout || command -v gtimeout || true)

if [[ -t 1 && -z ${NO_COLOR:-} && ${TERM:-dumb} != dumb ]]; then
    _C_PASS=$'\033[32m'
    _C_FAIL=$'\033[31m'
    _C_DIM=$'\033[2m'
    _C_OFF=$'\033[0m'
else
    _C_PASS='' _C_FAIL='' _C_DIM='' _C_OFF=''
fi

_tse_indent() {
    # Print stdin indented by six spaces, truncated to a sane number of lines.
    local line count=0
    while IFS= read -r line || [[ -n $line ]]; do
        count=$((count + 1))
        if (( count > _TSE_MAX_OUTPUT_LINES )); then
            printf '      %s... output truncated ...%s\n' "$_C_DIM" "$_C_OFF"
            return
        fi
        printf '      %s\n' "$line"
    done
    if (( count == 0 )); then
        printf '      %s(no output)%s\n' "$_C_DIM" "$_C_OFF"
    fi
}

_tse_matches() {
    local mode=$1 expected=$2 actual=$3
    case "$mode" in
        equals)       [[ $(printf '%s' "$actual" | tr -d '[:space:]') == "$(printf '%s' "$expected" | tr -d '[:space:]')" ]] ;;
        contains)     [[ $actual == *"$expected"* ]] ;;
        not-contains) [[ $actual != *"$expected"* ]] ;;
        matches)      [[ $actual =~ $expected ]] ;;
        *)            return 1 ;;
    esac
}

assert() {
    local description=$1; shift
    local command='' mode='' expected='' expectation='' retries=1 delay=1
    local tolerate_failure=0

    while (( $# )); do
        case "$1" in
            --run)          command=$2;     shift 2 ;;
            --equals)       mode=equals;       expected=$2; shift 2 ;;
            --contains)     mode=contains;     expected=$2; shift 2 ;;
            --not-contains) mode=not-contains; expected=$2; shift 2 ;;
            --matches)      mode=matches;      expected=$2; shift 2 ;;
            --expect)       expectation=$2; shift 2 ;;
            --retries)      retries=$2;     shift 2 ;;
            --delay)        delay=$2;       shift 2 ;;
            --even-if-it-fails) tolerate_failure=1; shift ;;
            *) printf 'assert: unknown option %s\n' "$1" >&2; return 2 ;;
        esac
    done

    if [[ -z $command || -z $mode ]]; then
        printf 'assert: --run and one matcher are required\n' >&2
        return 2
    fi

    # When verifying that an exercise really is broken, waiting out the full
    # recovery retry budget proves nothing and makes CI crawl. The cap absorbs
    # startup jitter without waiting for a recovery that is not coming.
    if [[ -n ${TSE_MAX_RETRIES:-} ]] && (( retries > TSE_MAX_RETRIES )); then
        retries=$TSE_MAX_RETRIES
    fi

    local output='' attempt=0 ok=1 status=0 died=0
    while (( attempt < retries )); do
        attempt=$((attempt + 1))
        # Bounded, once, here, rather than in each of the twenty five graders.
        #
        # A grader runs the customer's own request script, and several of those
        # are a bare curl with no time limit. A broken backend that holds the
        # connection open instead of refusing it, which is an ordinary way for a
        # service to be broken, hangs the grader with nothing printed. The
        # learner sees `tse check` stop, and CI sees a job time out half an hour
        # later naming nothing.
        #
        # `timeout` is not on every machine. Where it is missing the command
        # runs unbounded, which is what happened before, so this can only help.
        #
        # `-uo pipefail` matches what the sourced-in options give the `eval`
        # branch. Without it the same assertion reports a different exit status
        # depending on whether the machine has `timeout`, which is Linux and CI
        # against a stock Mac: a broken first stage of a pipeline is invisible
        # in one and fatal in the other.
        if [[ -n ${_TSE_TIMEOUT_BIN:-} ]]; then
            output=$("$_TSE_TIMEOUT_BIN" "${TSE_ASSERT_TIMEOUT:-60}" \
                     bash -uo pipefail -c "$command" 2>&1)
        else
            output=$(eval "$command" 2>&1)
        fi
        status=$?

        # Absence is only evidence when the command ran.
        #
        # `--not-contains` passes when a string is missing from the output. If
        # the command itself failed there is no output to be missing from, so
        # the assertion passes on an error message and reports success. Both
        # uses in the course were doing exactly that: sql/03 asks a stopped
        # database for a query plan, gets `service "postgres" is not running`,
        # observes no sequential scan in it, and grades the exercise complete.
        #
        # Only the negative matcher needs this. `--equals` and `--contains`
        # already have to see the thing they are looking for, and an error
        # message does not contain it. `--matches` is the author's own regex and
        # is left alone. `--even-if-it-fails` is the way out for an assertion
        # that genuinely expects a non-zero exit.
        died=0
        if (( status != 0 )) && [[ $mode == not-contains ]] && (( tolerate_failure == 0 )); then
            died=1
        elif _tse_matches "$mode" "$expected" "$output"; then
            ok=0
            break
        fi
        (( attempt < retries )) && sleep "$delay"
    done

    if (( ok == 0 )); then
        _TSE_PASSED=$((_TSE_PASSED + 1))
        printf '%sPASS%s  %s\n' "$_C_PASS" "$_C_OFF" "$description"
    else
        _TSE_FAILED=$((_TSE_FAILED + 1))
        printf '%sFAIL%s  %s\n' "$_C_FAIL" "$_C_OFF" "$description"
    fi

    printf '      %s$ %s%s\n' "$_C_DIM" "$command" "$_C_OFF"
    printf '%s' "$output" | _tse_indent

    if (( ok != 0 )); then
        if (( died )); then
            printf '      %sThe command itself failed, exit %d. What it did not print proves nothing.%s\n' \
                "$_C_FAIL" "$status" "$_C_OFF"
        fi
        printf '      %sExpected: %s%s\n' "$_C_FAIL" "${expectation:-$mode $expected}" "$_C_OFF"
    fi
    printf '\n'
}

finish() {
    local total=$((_TSE_PASSED + _TSE_FAILED))
    # A grader that asked nothing is not a grader that found nothing wrong.
    #
    # This used to print "0 of 0 checks passed" and exit 0, which every one of
    # the twenty five check.sh files would inherit the moment its assertions
    # ended up behind a condition that turned out false: a renamed variable, a
    # stale flag, an `if` that stopped matching. `tse verify` catches only the
    # version of that where the broken state passes too, so it is not cover for
    # this. Nothing else in the repository was watching.
    if (( total == 0 )); then
        printf '%sThis grader ran no checks at all, so it has proved nothing.%s\n' \
            "$_C_FAIL" "$_C_OFF"
        printf '      Its assertions are all behind a condition that was false.\n'
        exit 1
    fi
    if (( _TSE_FAILED == 0 )); then
        printf '%s%d of %d checks passed.%s\n' "$_C_PASS" "$_TSE_PASSED" "$total" "$_C_OFF"
        exit 0
    fi
    printf '%s%d of %d checks failed.%s\n' "$_C_FAIL" "$_TSE_FAILED" "$total" "$_C_OFF"
    exit 1
}
