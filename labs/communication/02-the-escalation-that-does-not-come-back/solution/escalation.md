# Escalation to the platform team

**Impact:** Halden Freight, enterprise, total loss of service for all users
from 06:00 to 09:12. Every request was accepted and closed with no response.
Found by the customer, not by us.

**Evidence:** the published mapping was `127.0.0.1:8100->8081/tcp` while the
application logged `server_started port=8080` on the way up. Requests to the
published address returned nothing. The container reported `Up (healthy)`
throughout, because the health check runs inside the container and connects
straight to the application, never crossing the mapping that was wrong.

**Confirmed:** application process health, clean application startup, database
availability, and that the fault was entirely in the published mapping.

**Ruled out:** application crash, dependency failure, credential or data
problem.

**Suspected cause:** last night's release changed the container-side target of
the published port from 8080 to 8081. The application has always listened on
8080.

**Request:** two things, and the second matters more than the first.

1. The one-digit fix is already in. Please confirm whether the same edit exists
   in any other service that shares this release template, because one
   misconfigured service is an incident and a shared template is an outage
   waiting for the next deploy.

2. We have no signal that can see this class of fault. Every check we own runs
   inside the container and passed for three hours while the service was
   completely unreachable. A check that connects from outside the published
   address would have caught this in seconds. Can the platform team own adding
   one, and tell me what is realistic, so I can hold to the date I gave the
   customer.
