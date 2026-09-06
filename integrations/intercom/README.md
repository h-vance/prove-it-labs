# Intercom: file a real failure as an Inbox conversation

A support engineer's day starts in the Inbox. This script puts a real ticket
there. It makes one call to the course's api stack with a revoked key, takes
the 401 the server returns, and opens a conversation from a fake customer in
an Intercom workspace. The message quotes the endpoint, the HTTP status, the
stable error code, and the request id, which is what you would ask a customer
for and what you would search the logs by.

Everything is standard library Python. Nothing to install.

## Setup

1. Start an [Intercom](https://www.intercom.com/) trial workspace.
2. Open the Developer Hub, create an app, and copy its access token. Intercom's
   [authentication guide](https://developers.intercom.com/docs/build-an-integration/learn-more/authentication)
   walks through it.
3. Keep the token out of this repository. `tse leaks` fails the build if a
   real credential is committed. The script asks for it when it runs, or
   reads `INTERCOM_TOKEN` from the environment if that is set.

## Run

Bring up the api stack. Any api exercise will do; the first one is the one the
ticket is about.

```bash
tools/tse start api/01-webhook-integration-rejected
```

See the message without touching Intercom:

```bash
python3 integrations/intercom/push_ticket.py --dry-run
```

Send it for real:

```bash
python3 integrations/intercom/push_ticket.py
```

It prints the conversation id. Open the Inbox and it is there, from Northwind
Freight. Run it again and it reuses the same contact rather than making a
second one.

## What it uses

- [Search contacts](https://developers.intercom.com/docs/references/rest-api/api.intercom.io/contacts/searchcontacts)
  by email, then [create a contact](https://developers.intercom.com/docs/references/rest-api/api.intercom.io/contacts/createcontact)
  only if there is none.
- [Create a conversation](https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/createconversation)
  from that contact with the message body.

The request id and error code come from `labs/api/_stack/api.py`, which
answers every error as RFC 9457 problem details with a stable `code` member.
The customer quotes both; the engineer branches on the code.
