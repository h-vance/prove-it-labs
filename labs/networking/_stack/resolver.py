"""The internal resolver. Answers the names the platform team publishes.

Deliberately ordinary, in the same way the gateway is. Nothing in here is
broken in any exercise: what changes between them is which records it was
configured with, and the point of the DNS exercise is that a correct, healthy,
running resolver handing back a wrong answer looks exactly like a working
network from every other angle.

Why this exists at all, rather than the exercise editing `/etc/hosts` or
pointing the client somewhere: `COMPOSE_OVERRIDE_KEYS` in tools/tse permits an
exercise to set `environment`, `user`, `group_add` and `ports`, and nothing
else. `extra_hosts` is the Compose twin of `hostAliases`, which the Kubernetes
side already refuses, and `dns` would let a contributed pull request point a
container's resolver at any address it chose. Both stay refused. So the only
way to teach a name resolving to the wrong place is a resolver in the stack,
configured by an environment variable, which is what this is.

Records come from LAB_RECORDS as `name=target`, comma separated:

    LAB_RECORDS: "reports.ardent.example=127.0.0.1"
    LAB_RECORDS: "reports.ardent.example=gateway"

A target is either a literal address or another name, and the second form is
what makes the fix readable: it says "point this record at the gateway" rather
than at an address nobody can know in advance, because Compose hands out a new
one every time the stack is recreated.

Logging follows gateway.py: logfmt, no timestamps, and only the records this
resolver answered itself. A relayed query is somebody else's answer and saying
so on every lookup would bury the two lines that matter.
"""
from __future__ import annotations

import os
import socket
import socketserver
import struct
import sys

PORT = 53
UPSTREAM = ("127.0.0.11", 53)
UPSTREAM_TIMEOUT_S = 5.0

# Long enough that a lookup is not repeated inside one command, short enough
# that a learner who fixes the record and runs `tse apply` is not then fighting
# a cached answer. Fixed rather than derived, because it is printed.
TTL = 30

TYPE_A = 1
CLASS_IN = 1

# QR=1 response, RD=1 copied from the query, RA=1 recursion available, rcode 0.
FLAGS_ANSWER = 0x8180

# A name in an answer is written once and pointed at from there. 0xC00C is the
# offset of the question's name: 0xC000 marks a pointer, 0x000C is 12, which is
# the length of the header the question follows.
NAME_POINTER = 0xC00C


def parse_records(raw: str) -> dict[str, str]:
    """LAB_RECORDS into {name: target}, refusing anything it cannot read.

    A resolver that silently ignored a malformed record would come up serving
    less than it was configured with, and the exercise would then look broken
    in a way that pointed at the content rather than at the typo.
    """
    records = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        name, separator, target = entry.partition("=")
        if not separator or not name.strip() or not target.strip():
            sys.exit(
                f"LAB_RECORDS entry {entry!r} is not `name=target`.\n"
                "It is set in the exercise's compose.override.yaml."
            )
        records[name.strip().rstrip(".").lower()] = target.strip()
    return records


def read_question_name(query: bytes) -> tuple[str, int]:
    """The name being asked about, and where the question's name ends.

    Refuses a compressed name. Compression points backwards at a name already
    written, and in a question there is nothing before it to point at, so a
    pointer here is a malformed query rather than something to follow.
    """
    labels = []
    offset = 12  # past the header
    while True:
        if offset >= len(query):
            raise ValueError("the question ran off the end of the query")
        length = query[offset]
        if length == 0:
            return ".".join(labels).lower(), offset + 1
        if length & 0xC0:
            raise ValueError("a compressed name in a question")
        offset += 1
        labels.append(query[offset:offset + length].decode("ascii", "replace"))
        offset += length


def address_for(target: str) -> str | None:
    """A literal address, or whatever the target name resolves to right now.

    Resolved per query rather than at startup on purpose. Compose assigns a new
    address every time a service is recreated, and `tse apply` recreates all of
    them, so a target cached at startup would be correct until the first time a
    learner applied their fix and wrong immediately afterwards.
    """
    try:
        socket.inet_aton(target)
    except OSError:
        pass
    else:
        return target

    try:
        return socket.getaddrinfo(target, None, socket.AF_INET)[0][4][0]
    except (OSError, IndexError):
        return None


class Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        query, sock = self.request
        if len(query) < 13:
            return  # not a query; nothing to answer and nothing to relay

        try:
            name, name_end = read_question_name(query)
        except ValueError:
            self.relay(query, sock)
            return

        target = self.server.records.get(name)
        if target is None:
            self.relay(query, sock)
            return

        question_end = name_end + 4  # qtype and qclass
        qtype, _ = struct.unpack("!HH", query[name_end:question_end])
        header = query[:2] + struct.pack(
            "!HHHHH", FLAGS_ANSWER, 1, 1 if qtype == TYPE_A else 0, 0, 0)
        reply = header + query[12:question_end]

        if qtype == TYPE_A:
            address = address_for(target)
            if address is None:
                # The record exists and its target does not resolve. Answering
                # with no address says exactly that, and is a different fact
                # from the name not existing.
                print(f"level=warn event=target_unresolved name={name} "
                      f"target={target}", flush=True)
                sock.sendto(reply, self.client_address)
                return
            reply += struct.pack("!HHHIH", NAME_POINTER, TYPE_A, CLASS_IN, TTL, 4)
            reply += socket.inet_aton(address)
            print(f"level=info event=answered name={name} type=A "
                  f"address={address}", flush=True)
        else:
            # The name exists and has no record of this type. Relaying instead
            # would hand back the upstream's opinion, which is that the name
            # does not exist at all, and a resolver that says a name exists for
            # one query type and not another is a lab bug rather than a lesson.
            print(f"level=info event=no_record name={name} type={qtype}",
                  flush=True)

        sock.sendto(reply, self.client_address)

    def relay(self, query: bytes, sock: socket.socket) -> None:
        """Hand the query to Docker's embedded DNS and pass its answer back.

        Untouched in both directions, including the id, so the client cannot
        tell this apart from asking Docker directly. That is what lets the two
        exercises already in this track keep resolving `gateway` and `reports`
        exactly as they did before this service existed.
        """
        upstream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        upstream.settimeout(UPSTREAM_TIMEOUT_S)
        try:
            upstream.sendto(query, UPSTREAM)
            answer, _ = upstream.recvfrom(4096)
        except OSError as error:
            print(f"level=error event=relay_failed reason={error}", flush=True)
            return
        finally:
            upstream.close()
        sock.sendto(answer, self.client_address)


class Server(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler, records: dict[str, str]):
        self.records = records
        super().__init__(address, handler)


def main() -> None:
    records = parse_records(os.environ.get("LAB_RECORDS", ""))

    try:
        server = Server(("0.0.0.0", PORT), Handler, records)
    except PermissionError:
        # Explain the failure rather than let it look like the content.
        #
        # This service runs as a non-root user with every capability dropped,
        # and it binds a port below 1024. That works because Docker sets
        # net.ipv4.ip_unprivileged_port_start=0 inside containers, which was
        # confirmed on a real daemon before this was written rather than
        # assumed. A daemon configured otherwise lands here.
        sys.exit(
            f"Could not bind port {PORT}.\n"
            "This resolver runs unprivileged and relies on Docker's default\n"
            "net.ipv4.ip_unprivileged_port_start=0. If your daemon sets that\n"
            "to 1024, the resolver needs cap_add: NET_BIND_SERVICE."
        )

    for name, target in sorted(records.items()):
        print(f"level=info event=record name={name} target={target}", flush=True)
    print(f"level=info event=server_started port={PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
