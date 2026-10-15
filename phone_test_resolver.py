"""
phone_test.py - send MDNS/1.0 queries from the phone (Pydroid 3) to the laptop.

Standalone: needs no other file, so you can copy just this one to the phone.
Run it, type the laptop's IP, then type names to look up (empty line = quit).
"""
import socket
import random
import time

PORT = 5300            # resolver port (copy of phone_test.py for testing the resolver)


def build(msg_type, headers):
    lines = [f"MDNS/1.0 {msg_type}"] + [f"{k}: {v}" for k, v in headers.items()]
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")


def parse(data):
    lines = data.decode("ascii").strip().split("\r\n")
    headers = dict(line.split(": ", 1) for line in lines[1:])
    return lines[0], headers


server_ip = input("Enter the server's IP: ").strip()
server = (server_ip, PORT)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(4.0)

# Show this phone's own IP 
sock.connect(server)
print("This device's IP:", sock.getsockname()[0])
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # fresh unconnected socket
sock.settimeout(4.0)

print("\nType a name to look up (e.g. www.neduet.lab). To ask for another type: mail.neduet.lab MX")
print("Empty Enter = quit, 'ping' = round-trip time\n")

while True:
    text = input("> ").strip()
    if not text:
        break

    qid = str(random.randint(1, 65535))
    if text.lower() == "ping":
        msg = build("PING", {"ID": qid})
    else:
        parts = text.split()
        name = parts[0]
        rtype = parts[1].upper() if len(parts) > 1 else "A"
        msg = build("QUERY", {"ID": qid, "NAME": name, "RTYPE": rtype})

    start = time.perf_counter()
    sock.sendto(msg, server)
    try:
        data, addr = sock.recvfrom(2048)
    except (socket.timeout, ConnectionResetError):   # Windows reports "port closed" as ConnectionResetError
        print("  No reply within 4 s. Check: is the IP correct? Is the server running? Firewall?\n")
        continue
    ms = (time.perf_counter() - start) * 1000

    start_line, h = parse(data)
    print(f"  {start_line}  from {addr[0]}  ({ms:.1f} ms)")
    for key, value in h.items():
        print(f"    {key}: {value}")
    print()
