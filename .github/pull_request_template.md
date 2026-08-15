## What this changes

<!-- One or two sentences. -->

## If this adds or changes an exercise

- [ ] `tools/tse verify <id>` passes, meaning it **fails broken and passes fixed**
- [ ] The ticket describes a symptom and names no technology or layer
- [ ] The grader was run against the plausible wrong fix, and rejected it
- [ ] `tools/tse record <id>` afterwards, and `tools/tse record --check <id>` matches

## Always

- [ ] `python3 tools/tests/test_meta.py && python3 tools/tests/test_content.py`
- [ ] `python3 tools/tests/test_scrub.py && python3 tools/tests/test_rubric.py`
- [ ] `tools/tests/smoke.sh`
- [ ] `tools/tse leaks`
- [ ] `tools/tse stop`, so no generated stack file is committed
- [ ] Site touched? `npm run build && npm run check:pages && npm run check:terminal && npm run a11y`

## Anything you are unsure about

<!-- Optional, and more useful than leaving it out. -->
