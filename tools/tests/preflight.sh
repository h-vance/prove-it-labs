#!/usr/bin/env bash
# Everything CI would check, on this machine, before you push.
#
# This is the gate that matters while the repository is private. The Docker
# half of verify.yml costs 73 of its 81 billable minutes, which is a private
# repository's entire monthly allowance in 27 pushes, so it runs on request
# only. The same work runs here for nothing.
#
#   tools/tests/preflight.sh            what your branch changed, against origin/main
#   tools/tests/preflight.sh --all      all 25 exercises, the full CI matrix
#   tools/tests/preflight.sh --fast     no Docker at all, about 20 seconds
#
# Which exercises the default picks is decided by `tse affected`, the same
# command the workflow uses, so this cannot check less than CI would.

set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT" || exit 1
TSE="$ROOT/tools/tse"

MODE=${1:-}
PASSED=0
FAILED=0
SKIPPED=0

if [[ -t 1 && -z ${NO_COLOR:-} && ${TERM:-dumb} != dumb ]]; then
    C_PASS=$'\033[32m'; C_FAIL=$'\033[31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
    C_PASS='' C_FAIL='' C_DIM='' C_OFF=''
fi

step() { printf '\n%s== %s%s\n' "$C_DIM" "$1" "$C_OFF"; }
pass() { PASSED=$((PASSED + 1)); printf '  %sok%s    %s\n' "$C_PASS" "$C_OFF" "$1"; }
skip() { SKIPPED=$((SKIPPED + 1)); printf '  %sskip%s  %s\n' "$C_DIM" "$C_OFF" "$1"; }
fail() {
    FAILED=$((FAILED + 1))
    printf '  %sFAIL%s  %s\n' "$C_FAIL" "$C_OFF" "$1"
    [[ -n ${2:-} ]] && printf '        %s\n' "$2"
    return 0
}

# Run a command quietly and report by name. The output is kept and shown only
# when it failed, because a wall of green output is how a real failure gets
# scrolled past.
run() {
    local label=$1; shift
    local log; log=$(mktemp)
    if "$@" >"$log" 2>&1; then
        pass "$label"
    else
        fail "$label" "$(tail -5 "$log" | sed 's/^/        /')"
    fi
    rm -f "$log"
}

# --------------------------------------------------------------------------- #
step "The gates that need nothing installed"

run "content, editorial and leak rules" python3 tools/tests/test_content.py
run "the meta parser"                   python3 tools/tests/test_meta.py
run "the output scrubber"               python3 tools/tests/test_scrub.py
run "the communication rubric"          python3 tools/tests/test_rubric.py
run "the leak scan over every file"     "$TSE" leaks
run "the CLI smoke test"                tools/tests/smoke.sh --fast

# --------------------------------------------------------------------------- #
step "Shell"

if command -v shellcheck >/dev/null 2>&1; then
    # shellcheck disable=SC2046  # the glob is the argument list, deliberately
    run "shellcheck" shellcheck --severity=info -e SC1091 \
        tools/lib/assert.sh tools/tests/smoke.sh tools/tests/preflight.sh \
        .devcontainer/post-create.sh \
        $(ls labs/*/*/check.sh labs/*/*/setup/*.sh labs/*/*/solution/*.sh \
             labs/*/_stack/*.sh 2>/dev/null)
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    # Not everyone has shellcheck and it is a CI requirement, so the container
    # is offered rather than the check being quietly skipped.
    run "shellcheck (via docker)" docker run --rm -v "$ROOT:/mnt" -w /mnt \
        koalaman/shellcheck-alpine:stable \
        sh -c 'find . -name "*.sh" -not -path "./site/node_modules/*" \
               | xargs shellcheck --severity=info -e SC1091'
else
    skip "shellcheck (not installed, and Docker is not running)"
fi

# --------------------------------------------------------------------------- #
step "The site"

# Run an npm script from site/ without leaving this shell in there, and
# without putting `run` inside a subshell. A subshell would throw away the
# pass and fail counters it just incremented, so a failing site check would
# print FAIL and still let this script report that it is safe to push.
site_run() {
    local label=$1 script=$2
    local log; log=$(mktemp)
    if ( cd "$ROOT/site" && npm run "$script" ) >"$log" 2>&1; then
        pass "$label"
    else
        fail "$label" "$(tail -6 "$log" | sed 's/^/        /')"
    fi
    rm -f "$log"
}

if [[ $MODE == --fast ]]; then
    skip "site build and checks (--fast)"
elif [[ ! -d site/node_modules ]]; then
    skip "site build and checks (run 'npm ci' in site/ first)"
else
    site_run "the site builds"  build
    site_run "types"            check
    site_run "page contents"    check:pages
    site_run "terminal replay"  check:terminal
    site_run "accessibility"    a11y
fi

# --------------------------------------------------------------------------- #
# The expensive half, and the reason this file exists.
step "The exercises"

if [[ $MODE == --fast ]]; then
    skip "every exercise (--fast)"
elif ! docker info >/dev/null 2>&1; then
    skip "every exercise (Docker is not running)"
else
    if [[ $MODE == --all ]]; then
        exercises=$("$TSE" list --ids)
        why="all of them, because you asked for --all"
    else
        # The same rule CI uses, fed the same kind of input: what this branch
        # changed, plus anything not yet committed, since the point of running
        # this is to find out before you commit.
        base=$(git merge-base origin/main HEAD 2>/dev/null || echo "")
        if [[ -z $base ]]; then
            exercises=$("$TSE" list --ids)
            why="all of them, because there is no origin/main to compare against"
        else
            changed=$( { git diff --name-only "$base" HEAD; git status --porcelain \
                         | sed 's/^...//'; } | sort -u )
            exercises=$(printf '%s\n' "$changed" | "$TSE" affected)
            why="what this branch changed since origin/main"
        fi
    fi

    count=$(printf '%s' "$exercises" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
    printf '  %s%s exercise(s): %s%s\n' "$C_DIM" "$count" "$why" "$C_OFF"

    for exercise in $(printf '%s' "$exercises" | python3 -c \
                      'import json,sys; print("\n".join(json.load(sys.stdin)))'); do
        run "$exercise fails broken and passes fixed" "$TSE" verify "$exercise"
        if [[ -f "labs/$exercise/transcript.json" ]]; then
            run "$exercise still records what it claims" "$TSE" record --check "$exercise"
        else
            skip "$exercise has no transcript to check"
        fi
    done
fi

# --------------------------------------------------------------------------- #
printf '\n%d passed, %d failed, %d skipped\n' "$PASSED" "$FAILED" "$SKIPPED"
if (( FAILED == 0 )); then
    printf '%sSafe to push.%s\n' "$C_PASS" "$C_OFF"
    exit 0
fi
printf '%sNot safe to push.%s\n' "$C_FAIL" "$C_OFF"
exit 1
