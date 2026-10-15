"""
ttl_test.py - TTL experiment (Section 7.2). Run on the LAPTOP or any host.

Usage:  py ttl_test.py <resolver_ip> <name> [interval_s] [duration_s]
Example: py ttl_test.py 127.0.0.1 fast.neduet.lab 2 120

Sends FLUSH first (clean start), then one QUERY every interval_s seconds for
duration_s seconds. SRC: AUTH = cache miss, SRC: CACHE = cache hit.
"""
import socket, sys, time, random
from common import build, parse, RESOLVER_PORT

ip, name = sys.argv[1], sys.argv[2]
interval = float(sys.argv[3]) if len(sys.argv) > 3 else 2
duration = float(sys.argv[4]) if len(sys.argv) > 4 else 120

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(4)

def ask(msg_type, headers):
    s.sendto(build(msg_type, headers), (ip, RESOLVER_PORT))
    data, _ = s.recvfrom(65535)
    return parse(data)[1]

ask("FLUSH", {"ID": random.randint(1, 65535)})
sent = misses = hits = other = 0
start = time.time()
while time.time() - start < duration:
    try:
        h = ask("QUERY", {"ID": random.randint(1, 65535), "NAME": name, "RTYPE": "A"})
        src = h.get("SRC")
        if h.get("STATUS") == "200" and src == "AUTH": misses += 1
        elif h.get("STATUS") == "200" and src == "CACHE": hits += 1
        else: other += 1
        print(f"{time.time()-start:6.1f}s  status={h.get('STATUS')} src={src} ttl_left={h.get('TTL')}")
    except socket.timeout:
        other += 1
        print(f"{time.time()-start:6.1f}s  timeout")
    sent += 1
    time.sleep(interval)

print(f"\n{name}: queries={sent}  misses(AUTH)={misses}  hits(CACHE)={hits}  other={other}")
if sent:
    print(f"upstream traffic saved = {hits/sent*100:.1f}%")
