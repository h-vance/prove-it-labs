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

    local output='' attempt=0 ok=1
    while (( attempt < retries )); do
        attempt=$((attempt + 1))
        output=$(eval "$command" 2>&1)
        if _tse_matches "$mode" "$expected" "$output"; then
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
        printf '      %sExpected: %s%s\n' "$_C_FAIL" "${expectation:-$mode $expected}" "$_C_OFF"
    fi
    printf '\n'
}

finish() {
    local total=$((_TSE_PASSED + _TSE_FAILED))
    if (( _TSE_FAILED == 0 )); then
        printf '%s%d of %d checks passed.%s\n' "$_C_PASS" "$_TSE_PASSED" "$total" "$_C_OFF"
        exit 0
    fi
    printf '%s%d of %d checks failed.%s\n' "$_C_FAIL" "$_TSE_FAILED" "$total" "$_C_OFF"
    exit 1
}
