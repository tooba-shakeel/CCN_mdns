"""
resolver.py - MDNS/1.0 caching resolver (Laptop).

Run:  py resolver.py
Listens on UDP 5300 for clients. On a cache miss it asks the authoritative
server (AUTH_ADDR) on UDP 5400: 1 s wait, 3 attempts, same ID, then 504.
Only 200 answers are cached (TTL 0 is never cached).
"""
import math
import socket
import time
from common import build, parse, require, log, RECORD_TYPES, RESOLVER_PORT, AUTH_PORT

ROLE = "RESOLVER"

# Home testing: 127.0.0.1.  Experiment day: Phone 1's IP (laptop's Default Gateway).
AUTH_ADDR = ("127.0.0.1", AUTH_PORT)

UPSTREAM_WAIT = 1.0      # seconds to wait per attempt
UPSTREAM_TRIES = 3

cache = {}               # (name, rtype) -> (value, ttl, stored_time)


def ask_auth(up_sock, qid, name, rtype):
    """Forward the QUERY to the authoritative server. Returns reply headers or None."""
    query = build("QUERY", {"ID": qid, "NAME": name, "RTYPE": rtype})
    for attempt in range(1, UPSTREAM_TRIES + 1):
        up_sock.sendto(query, AUTH_ADDR)
        deadline = time.monotonic() + UPSTREAM_WAIT
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            up_sock.settimeout(left)
            try:
                data, _ = up_sock.recvfrom(65535)     # largest UDP datagram, nothing cut off
            except socket.timeout:
                break
            except OSError:
                # Windows reports "port unreachable" (server stopped) as an error.
                # Treat it as no answer and still use the full 1 s, so timing is unchanged.
                time.sleep(max(0.0, deadline - time.monotonic()))
                break
            try:
                msg_type, h = parse(data)
            except ValueError:
                continue                                  # garbage, keep waiting
            if msg_type != "RESPONSE" or h.get("ID") != str(qid):
                log(ROLE, f"discard late/unknown reply id={h.get('ID')} (waiting for {qid})")
                continue                                  # late reply to an earlier query
            return h
        log(ROLE, f"TIMEOUT attempt {attempt}/{UPSTREAM_TRIES} id={qid} {name} {rtype}")
    return None


def handle(data, addr, up_sock):
    """Work out the reply (bytes) for one datagram from a client."""
    try:
        msg_type, h = parse(data)
    except ValueError as e:
        log(ROLE, f"400 malformed from {addr}: {e}")
        return build("RESPONSE", {"ID": "0", "STATUS": "400"})

    qid = h.get("ID", "0")

    if msg_type == "PING":
        return build("PONG", {"ID": qid})

    if msg_type == "FLUSH":
        cache.clear()
        log(ROLE, f"FLUSH id={qid} cache cleared")
        return build("RESPONSE", {"ID": qid, "STATUS": "200"})

    if msg_type != "QUERY":
        log(ROLE, f"501 unsupported message type {msg_type}")
        return build("RESPONSE", {"ID": qid, "STATUS": "501"})

    try:
        require(h, "ID", "NAME", "RTYPE")
    except ValueError as e:
        log(ROLE, f"400 {e}")
        return build("RESPONSE", {"ID": qid, "STATUS": "400"})

    name, rtype = h["NAME"].lower(), h["RTYPE"].upper()
    if rtype not in RECORD_TYPES:
        log(ROLE, f"501 unsupported RTYPE {rtype} id={qid}")
        return build("RESPONSE", {"ID": qid, "NAME": name, "RTYPE": rtype, "STATUS": "501"})

    # ---- cache lookup ----
    key = (name, rtype)
    entry = cache.get(key)
    now = time.monotonic()
    if entry:
        value, ttl, stored = entry
        if now < stored + ttl:
            left = max(1, math.ceil(stored + ttl - now))
            log(ROLE, f"HIT id={qid} {name} {rtype} ttl_left={left}")
            return build("RESPONSE", {"ID": qid, "NAME": name, "RTYPE": rtype,
                                      "STATUS": "200", "TTL": left,
                                      "SRC": "CACHE", "VALUE": value})
        del cache[key]                                    # expired

    log(ROLE, f"MISS id={qid} {name} {rtype}")
    reply = ask_auth(up_sock, qid, name, rtype)
    if reply is None:
        log(ROLE, f"504 no answer from authoritative server id={qid} {name} {rtype}")
        return build("RESPONSE", {"ID": qid, "NAME": name, "RTYPE": rtype, "STATUS": "504"})

    if reply.get("STATUS") == "200":
        try:
            ttl, value = int(reply["TTL"]), reply["VALUE"]
        except (KeyError, ValueError):
            log(ROLE, f"400 bad 200 reply from authoritative server id={qid}")
            return build("RESPONSE", {"ID": qid, "NAME": name, "RTYPE": rtype, "STATUS": "400"})
        if ttl > 0:
            cache[key] = (value, ttl, time.monotonic())
            log(ROLE, f"CACHED {name} {rtype} ttl={ttl}")
    log(ROLE, f"UPSTREAM id={qid} {name} {rtype} -> {reply.get('STATUS')}")
    reply["ID"] = qid
    return build("RESPONSE", reply)                       # 404/501 are relayed, not cached


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)      # clients talk to this
    sock.bind(("0.0.0.0", RESOLVER_PORT))
    up_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # resolver -> auth server
    log(ROLE, f"listening on UDP {RESOLVER_PORT}, authoritative server = {AUTH_ADDR[0]}:{AUTH_ADDR[1]}")

    while True:
        try:
            data, addr = sock.recvfrom(65535)             # largest UDP datagram, nothing cut off
        except OSError as e:                              # e.g. Windows reports an earlier reply as undeliverable
            log(ROLE, f"receive error ignored: {e}")
            continue
        try:
            reply = handle(data, addr, up_sock)
            sock.sendto(reply, addr)
        except Exception as e:                            # never let one bad packet kill the resolver
            log(ROLE, f"ERROR {e!r}")


if __name__ == "__main__":
    main()
