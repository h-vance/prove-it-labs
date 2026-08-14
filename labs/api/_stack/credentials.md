# Credential reference

What the customer's integration team gave us. This is the sort of reference a
support engineer normally has: enough to reproduce, never the production secret
itself.

All values are synthetic and work only against this lab.

## Webhook API keys

| Key | State | Notes |
|---|---|---|
| `wk_live_active_3c95` | active | Issued 2026-08-12 during the scheduled rotation |
| `wk_live_revoked_8f21` | revoked | Revoked 2026-08-12, replaced by the key above |

## Report tokens

| Token | Scopes | Notes |
|---|---|---|
| `tok_viewer_5d10` | `reports:read` | Default token issued to all workspace members |
| `tok_admin_9b44` | `reports:read`, `reports:admin` | Required for report export |

## Base URL

`http://127.0.0.1:8101`

The v1 API was withdrawn on 2026-08-01. Current routes are served under `/v2`.
