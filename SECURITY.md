# Security

## This repository contains deliberately broken systems

That is the point of it, so it is worth being explicit about what is
intentional and what would be a real problem.

**Intentional, and not vulnerabilities:**

- Services that fail to start, crash, run out of resources, or reject valid
  requests. Each one is an exercise.
- An expired certificate and a certificate with the wrong name on it, in
  `labs/networking`. Both are issued at image build by a throwaway internal CA
  that exists only inside the container.
- Synthetic credentials in seed data and configuration, such as
  `rp_live_synthetic_9f21`. They authenticate nothing and reach nothing.
- Permissions and group memberships that are wrong on purpose, in `labs/linux`.

**Everything runs on your own machine.** No lab publishes a port beyond
`127.0.0.1`, no lab calls out to the internet at runtime, and nothing reports
usage anywhere. Addresses that look external, such as `reports.example.invalid`,
use reserved domains from RFC 6761 and RFC 2606 and do not resolve.

Do not run these stacks on a shared or internet-facing host. They are built to
be broken, and some of them are broken in ways that are only safe because
nothing else can reach them.

## Reporting something real

If you find a genuine vulnerability, meaning something that could affect a
person running this course rather than something a lab is teaching, please open
a [security advisory](https://github.com/h-vance/prove-it-labs/security/advisories/new)
rather than a public issue.

Things worth reporting:

- Anything in a lab that can reach outside the container it runs in.
- A real credential, key, or piece of personal data committed anywhere in the
  tree or in its history. `tools/tse leaks` scans every tracked file on every
  push and `tools/tse leaks --history` scans the history, but a pattern that was
  never written cannot fire.
- Anything in `tools/tse` that executes untrusted input.

There is no bounty. There is a fast reply and public credit if you would like it.
