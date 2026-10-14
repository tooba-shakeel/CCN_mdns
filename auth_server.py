"""
auth_server.py - MDNS/1.0 authoritative name server (Host A).

Run:  python auth_server.py
Listens on UDP 5400 and answers QUERY / PING from the resolver using zone.txt.
"""
import os
import socket
from common import build, parse, require, log, RECORD_TYPES, AUTH_PORT, HERE

ROLE = "AUTH"
def load_zone(path=os.path.join(HERE, "zone.txt")):
    #Read zone.txt into {(name, rtype): (value, ttl)}. Lines starting with # are comments.
    zone = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, rtype, value, ttl = line.split()
            zone[(name.lower(), rtype.upper())] = (value, int(ttl))
    return zone


def handle(data, zone):
    #Work out the reply (bytes) for one received datagram.
    try:
        msg_type, h = parse(data)
    except ValueError as e:
        log(ROLE, f"400 malformed: {e}")
        return build("RESPONSE", {"ID": "0", "STATUS": "400"})

    qid = h.get("ID", "0")

    if msg_type == "PING":
        return build("PONG", {"ID": qid})

    if msg_type != "QUERY":                       # RESPONSE, PONG, FLUSH, unknown
        log(ROLE, f"501 unsupported message type {msg_type}")
        return build("RESPONSE", {"ID": qid, "STATUS": "501"})

    try:
        require(h, "ID", "NAME", "RTYPE")
    except ValueError as e:
        log(ROLE, f"400 {e}")
        return build("RESPONSE", {"ID": qid, "STATUS": "400"})

    name, rtype = h["NAME"].lower(), h["RTYPE"].upper()
    reply = {"ID": qid, "NAME": name, "RTYPE": rtype}

    if rtype not in RECORD_TYPES:
        reply["STATUS"] = "501"
    elif (name, rtype) in zone:
        value, ttl = zone[(name, rtype)]
        reply.update({"STATUS": "200", "TTL": ttl, "SRC": "AUTH", "VALUE": value})
    else:
        reply.update({"STATUS": "404", "SRC": "AUTH"})

    log(ROLE, f"QUERY id={qid} {name} {rtype} -> {reply['STATUS']}")
    return build("RESPONSE", reply)
def main():
    zone = load_zone()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    # UDP
    sock.bind(("0.0.0.0", AUTH_PORT))                          # all interfaces
    log(ROLE, f"loaded {len(zone)} records, listening on UDP {AUTH_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(65535)    # largest possible UDP datagram, so nothing is cut off
        except OSError as e:                      # e.g. Windows reports an earlier reply as undeliverable
            log(ROLE, f"receive error ignored: {e}")
            continue
        reply = handle(data, zone)
        sock.sendto(reply, addr)
if __name__ == "__main__":
    main()
