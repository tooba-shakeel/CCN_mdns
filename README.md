# MDNS/1.0 – Mini DNS Service (CS-327 CCN CEP, Option B)

A small DNS system with our own text-based application layer protocol (MDNS/1.0) over UDP, written in Python 3 using only the built-in socket module.

## Deployment

- **Phone 1** (also the Wi-Fi hotspot): authoritative server, runs auth_server.py on UDP port 5400
- **Laptop** (also runs Wireshark): caching resolver, runs resolver.py on UDP port 5300
- **Phone 2**: client, runs client.py on any free port

Query path: client → resolver → authoritative server (only on a cache miss).

## Team (3 members)

- **Member 1 (CS-018):** message format, authoritative server, zone file (Phone 1); report: Introduction, Protocol specification (R1), Implementation (R2), design tension 7.1
- **Member 2 (CS-020):** caching resolver, laptop setup, Wireshark; report: Deployment (R3), Packet capture (R5), Sustainability, design tension 7.2
- **Member 3 (CS-302):** client with retry (Phone 2), failure tests, measurement and plotting scripts; report: Transport choice (R4), Performance (R6), Behaviour under failure (R7), design tension 7.3

## Files

- **common.py**: Member 1 (CS-018), every device, done and tested
- **zone.txt**: Member 1 (CS-018), Phone 1, done and tested
- **auth_server.py**: Member 1 (CS-018), Phone 1, done and tested
- **phone_test.py**: Member 1 (CS-018), any phone or laptop (test tool), done and tested
- **binary_size.py**: Member 1 (CS-018), laptop, text vs binary size for design tension 7.1, done and tested
- **resolver.py**: Member 2 (CS-020), Laptop, done and tested
- **client.py**: Member 3 (CS-302), Phone 2, to do
- **measure.py, plot.py**: Member 3 (CS-302), Laptop / Phone 2, to do

## Fixed protocol values
- **Transport:** UDP, one message per datagram, max 1024 bytes
- **Resolver port:** 5300 (common.RESOLVER_PORT)
- **Auth server port:** 5400 (common.AUTH_PORT)
- **Message types:** QUERY, RESPONSE, PING, PONG, FLUSH
- **Header fields:** ID, NAME, RTYPE, STATUS, TTL, VALUE, SRC
- **Record types:** A, CNAME, MX
- **Status codes:** 200 OK, 400 Bad Request, 404 Not Found, 501 Not Implemented, 504 Upstream Timeout
- **Client timeout:** 4 s, 3 attempts, same ID on every retry
- **Resolver to auth timeout:** 1 s, 3 attempts, then reply 504
- **Cache:** only 200 answers; valid while now < stored time + TTL; TTL 0 is never cached; a cached answer is sent with the remaining TTL and SRC: CACHE

**Message layout** (every line ends with \r\n and an empty line ends the message). Example:

MDNS/1.0 QUERY\
ID: 36387\
NAME: www\.neduet.lab\
RTYPE: A

## Zone records (zone.txt)

Each line is: name, type, value, TTL in seconds. Lines starting with # are comments. Restart auth_server.py after editing the file.

- **www\.neduet.lab** (A): 10.0.0.5, TTL 60, main test name
- **cis.neduet.lab** (A): 10.0.0.7, TTL 60, second A record
- **mail.neduet.lab** (MX): 10.0.0.9, TTL 120, MX record
- **web.neduet.lab** (CNAME): www\.neduet.lab, TTL 60, alias
- **fast.neduet.lab** (A): 10.0.0.21, TTL 5, TTL experiment (expires quickly)
- **slow.neduet.lab** (A): 10.0.0.22, TTL 300, TTL experiment (stays cached)
- **nocache.neduet.lab** (A): 10.0.0.23, TTL 0, must never be cached (always a miss)
- **a-very-long-host-name-…neduet.lab** (A): 10.0.0.24, TTL 60, large message size test

Any name not in the list (for example xyz.neduet.lab) returns 404.

## Using common.py

- **build(type, fields):** turns a message type and its fields into bytes ready to send, for example build("QUERY", {"ID": 4821, "NAME": "www\.neduet.lab", "RTYPE": "A"})
- **parse(data):** turns received bytes back into (type, fields); raises ValueError if the message is malformed
- **require(fields, "ID", "NAME", "RTYPE"):** raises ValueError if a field is missing
- **log(role, text):** prints a timestamped line and appends it to auth.log / resolver.log in the same folder as the code

Notes:

- parse() returns every value as a string (for example TTL is "60"), so use int() where needed.
- parse() only raises the error; the program that called it decides to reply 400.

## Running

Use py instead of python if python is not on PATH. Start in this order:

1. **Phone 1:** py auth_server.py (listens on UDP 5400)
2. **Laptop:** py resolver.py (set AUTH_ADDR to Phone 1's IP)
3. **Phone 2:** py client.py (set RESOLVER to the laptop's IP)

On Windows, set the Wi-Fi network to **Private** and allow Python through the firewall the first time.

### Running the auth server on Phone 1 (Pydroid 3)

1. Copy common.py, auth_server.py and zone.txt into **one folder** on the phone (exact names).
2. Turn on the phone's mobile hotspot and connect the laptop to it.
3. Open auth_server.py in Pydroid 3 and press Run. Expect: "loaded 8 records, listening on UDP 5400".
4. Keep the screen on; Android may pause the app when the screen turns off.
5. Phone 1's IP is the **Default Gateway** shown by ipconfig on the laptop.

## Quick test of the auth server

1. Start auth_server.py (on a laptop or Phone 1).
2. Run phone_test.py on another device on the same network, enter the server's IP, then type:
    - www\.neduet.lab → 200, VALUE: 10.0.0.5
    - mail.neduet.lab MX → 200, VALUE: 10.0.0.9
    - web.neduet.lab CNAME → 200, VALUE: www\.neduet.lab
    - xyz.neduet.lab → 404
    - www\.neduet.lab AAAA → 501
    - ping → PONG
3. In Wireshark use the filter udp.port == 5400 to see the packets.
