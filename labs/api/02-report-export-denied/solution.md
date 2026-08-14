# Solution: export fails for one user but works for another

## What the evidence proved

| Evidence | What it proved | What it did not prove |
|---|---|---|
| Same page, same network, one user works | Not the browser, network, or the feature in general | Which user attribute differs |
| `HTTP 403`, not `401` | She is authenticated. The API knows who she is | That anything is broken |
| `"code": "insufficient_scope"` | The refusal is about permission, not identity | Which scope she has |
| `"required_scope": "reports:admin"` | Exactly what the operation demands | |
| `credentials.md` | The default member token carries only `reports:read` | |

## Root cause

Nothing is broken. The analyst holds the default workspace member token, which
carries `reports:read`. Exporting the incident report requires `reports:admin`,
which her team lead has and she does not. The API is behaving exactly as
designed.

This is a **permissions request**, not an incident. Classifying it correctly is
the entire value you add here, because it routes to their workspace
administrator instead of into an engineering queue where it would sit.

## The distinction that decides the ticket

| Status | Meaning | Typical cause | Who acts |
|---|---|---|---|
| `401` | We do not know who you are | Missing, invalid, or expired credential | Customer or whoever rotated it |
| `403` | We know exactly who you are, and no | Missing scope, role, or plan entitlement | Account administrator |

The customer's own reasoning was sound and led them to the wrong place: "her
login definitely works" is true, and it is the reason this is a 403 rather than
a 401.

## Scoped fix

To prove the diagnosis, run the same request with a token that carries the
scope:

```bash
TOKEN="tok_admin_9b44"
```

Then `tse check`.

Understand what you did and did not do. You proved which scope is required. You
did **not** grant her access, and you should not: elevating a user's permissions
is the customer administrator's decision, not support's.

## Customer update

> I reproduced the failure. Her account and login are working correctly, so
> nothing is wrong with her access in general. The export is refused because it
> requires the `reports:admin` permission, and her account currently has
> `reports:read`, which is the default for workspace members. That is why your
> team lead can export and she cannot. Your workspace administrator can grant
> that permission from the members page, and the export will work immediately
> after. There is no bug and no action needed from us. If you would like, I can
> confirm once her permission is updated.

Note what this avoids. It does not say "you do not have access", which reads as
a brush-off. It names the exact permission, says who can grant it, and offers to
verify.

## Engineering escalation, if you needed one

None. This is working as designed. If anything, the feedback worth passing on is
product-facing rather than engineering-facing:

> The export button is visible to users who lack `reports:admin`, so the failure
> is discovered only after the attempt. Worth considering whether the control
> should be disabled with an explanatory tooltip instead.

Support engineers who notice this pattern and report it are the ones who get
promoted, because a permissions ticket that recurs weekly is a design problem.

## Say it out loud (90 seconds)

> The customer has already ruled out a lot for me: same page, same network, one
> user can do it and one cannot. So I am looking for something that differs
> between two accounts. I would reproduce the failing request and read the
> status code, because the difference between 401 and 403 decides who owns this.
> Here it is a 403, which means she is authenticated and we know exactly who she
> is, and we are refusing anyway. That is consistent with what the customer told
> me, that her login works fine. The body names the required scope as
> reports:admin, and her token carries reports:read, which is the default for
> members. So this is not a bug, it is a permissions gap, and it resolves with
> their workspace administrator rather than with us. For the customer I would
> name the exact permission, confirm her account is otherwise healthy, and offer
> to verify once it is granted.
