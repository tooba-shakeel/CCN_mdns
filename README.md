# MDNS/1.0 – Mini DNS Service (CS-327 CCN CEP, Option B)

A small DNS system with our own text-based application layer protocol (MDNS/1.0) over UDP, written in Python 3 using only the built-in socket module. The authoritative server, the caching resolver and the client run on three separate devices.

## Deployment

All three devices are connected by Wi-Fi to the same access point (home router, subnet 192.168.18.0/24, gateway 192.168.18.1).

- **Host A – Phone 1** (Android, Pydroid 3): authoritative server, runs auth_server.py and zone.txt, IP 192.168.18.2, UDP port 5400
- **Host B – Laptop** (Windows 11, Python 3.11): caching resolver and Wireshark, runs resolver.py, IP 192.168.18.6, UDP port 5300
- **Host C – Phone 2** (Android, Pydroid 3): client, runs client.py and the test scripts, IP 192.168.18.3, temporary port chosen by the OS

Query path: client → resolver → authoritative server (only on a cache miss). On a cache hit the resolver answers from its cache and the authoritative server is not contacted.

The IP addresses are given out by the router and can change on another day. Check them with ipconfig (laptop) or the phone's Wi-Fi details before running, and update AUTH_ADDR in resolver.py and RESOLVER in client.py if needed.

## Team (3 members)

- **Tooba Muhammad Shakeel (CS-018):** message format (common.py), authoritative server, zone file, binary size comparison; report: Introduction, Protocol specification (R1), Implementation on sockets (R2), design tensions 7.1 and 7.4
- **Syeda Sameen Abidi (CS-020):** caching resolver, laptop setup, Wireshark, TTL experiment; report: Deployment (R3), Packet capture (R5), design tension 7.2, Sustainability
- **Ayesha Aziz (CS-302):** client with retry, measurement, workload, failure tests and plotting scripts; report: Transport choice (R4), Performance (R6), design tension 7.3, Behaviour under failure (R7)

## Files

- **common.py** (CS-018, every device): build(), parse(), require(), log() and the fixed protocol values
- **zone.txt** (CS-018, Phone 1): the 8 zone records
- **auth_server.py** (CS-018, Phone 1): authoritative server on UDP 5400
- **phone_test.py** (CS-018, any device): small tool to query the auth server directly
- **binary_size.py** (CS-018, laptop): text vs binary message size (report Table 9, Section 7.1)
- **resolver.py** (CS-020, laptop): caching resolver on UDP 5300
- **ttl_test.py** (CS-020, laptop): TTL experiment (report Table 10, Section 7.2)
- **client.py** (CS-302, Phone 2): client: interactive or one-shot queries, PING, FLUSH, retry
- **measure.py** (CS-302, Phone 2): 20 repetitions of ping, cache miss, cache hit and TTL 0 lookups → results.csv (Table 8)
- **workload.py** (CS-302, Phone 2): throughput and cache hit rate → workload_results.csv, workload_summary.txt (Sections 6 and 8)
- **failure_tests.py** (CS-302, Phone 2): guided failure tests → failure_results.txt (Table 11, Section 9)
- **plot.py** (CS-302, laptop): graphs from results.csv (Figure 7)

All files are done and tested on the three devices.

## Fixed protocol values

- **Transport:** UDP, one message per datagram, max 1024 bytes
- **Resolver port:** 5300 (common.RESOLVER_PORT)
- **Auth server port:** 5400 (common.AUTH_PORT)
- **Message types:** QUERY, RESPONSE, PING, PONG, FLUSH
- **Header fields:** ID, NAME, RTYPE, STATUS, TTL, VALUE, SRC
- **Record types:** A, CNAME, MX
- **Status codes:** 200 OK, 400 Bad Request, 404 Not Found, 501 Not Implemented, 504 Upstream Timeout
- **Client timeout:** 4 s per attempt, 3 attempts, same ID on every attempt
- **Resolver to auth timeout:** 1 s per attempt, 3 attempts, then reply 504
- **Cache:** only 200 answers; valid while now < stored time + TTL; TTL 0 is never cached; a cached answer is sent with the remaining TTL and SRC: CACHE; the cache is kept in memory only, so it is empty after a restart or a FLUSH

**Message layout** (every line ends with \r\n and an empty line ends the message). Example:

```
MDNS/1.0 QUERY
ID: 36387
NAME: www.neduet.lab
RTYPE: A

```

## Zone records (zone.txt)

Each line is: name, type, value, TTL in seconds. Lines starting with # are comments. Restart auth_server.py after editing the file.

- **www.neduet.lab** (A): 10.0.0.5, TTL 60, main test name
- **cis.neduet.lab** (A): 10.0.0.7, TTL 60, second A record
- **mail.neduet.lab** (MX): 10.0.0.9, TTL 120, MX record
- **web.neduet.lab** (CNAME): www.neduet.lab, TTL 60, alias
- **fast.neduet.lab** (A): 10.0.0.21, TTL 5, TTL experiment (expires quickly)
- **slow.neduet.lab** (A): 10.0.0.22, TTL 300, TTL experiment (stays cached)
- **nocache.neduet.lab** (A): 10.0.0.23, TTL 0, must never be cached (always a miss)
- **a-very-long-host-name-…neduet.lab** (A): 10.0.0.24, TTL 60, large message size test

Any name not in the list (for example xyz.neduet.lab) returns 404.

## Using common.py

- **build(type, fields):** turns a message type and its fields into bytes ready to send, for example `build("QUERY", {"ID": 4821, "NAME": "www.neduet.lab", "RTYPE": "A"})`
- **parse(data):** turns received bytes back into (type, fields); raises ValueError if the message is malformed
- **require(fields, "ID", "NAME", "RTYPE"):** raises ValueError if a field is missing
- **log(role, text):** prints a timestamped line and appends it to auth.log, resolver.log or client.log in the same folder as the code

Notes:

- parse() returns every value as a string (for example TTL is "60"), so use int() where needed.
- parse() only raises the error; the program that called it decides to reply 400.

## Running

Use `py` instead of `python` if python is not on PATH. Only plot.py needs a third-party package (`py -m pip install matplotlib`). Start in this order:

1. **Phone 1:** `auth_server.py` → expect "loaded 8 records, listening on UDP 5400"
2. **Laptop:** `py resolver.py` (AUTH_ADDR = Phone 1's IP)
3. **Phone 2:** `client.py` (RESOLVER = the laptop's IP), then type a name, `ping` or `flush`

On Windows, set the Wi-Fi network to **Private** and allow Python through the firewall the first time, otherwise the phones cannot reach the resolver.

### Running on the phones (Pydroid 3)

1. Copy the files into **one folder** on the phone with their exact names: common.py, auth_server.py and zone.txt on Phone 1; common.py, client.py and the test scripts on Phone 2.
2. Connect the phone to the same Wi-Fi as the laptop.
3. Open the program in Pydroid 3 and press Run.
4. Keep the screen on and the phone awake. When the screen turns off, Android's Wi-Fi power-save mode delays packets by up to a few hundred milliseconds (this caused the spikes in our first measurement run).

## Experiments (as used in the report)

- **R6, Table 8, Figure 7:** Phone 2: `measure.py`, then laptop: `py plot.py` → results.csv, hit_vs_miss.png, summary.png
- **R6 throughput, Section 8 hit rate:** Phone 2: `workload.py` → workload_results.csv, workload_summary.txt
- **Section 7.1, Table 9:** laptop: `py binary_size.py` → sizes printed on screen
- **Section 7.2, Table 10:** laptop: `py ttl_test.py 192.168.18.6 fast.neduet.lab 2 120` (and the same for slow.neduet.lab) → printed on screen
- **R7, Table 11:** Phone 2: `failure_tests.py`, then stop and start the servers when it asks → failure_results.txt
- **R5, Figures 5 and 9:** Wireshark on the laptop's Wi-Fi interface with the filter `udp.port == 5300 || udp.port == 5400` → main_experiment.pcapng, experiment_failure.pcapng

## Quick test of the auth server

1. Start auth_server.py (on a laptop or Phone 1).
2. Run phone_test.py on another device on the same network, enter the server's IP, then type:
    - www.neduet.lab → 200, VALUE: 10.0.0.5
    - mail.neduet.lab MX → 200, VALUE: 10.0.0.9
    - web.neduet.lab CNAME → 200, VALUE: www.neduet.lab
    - xyz.neduet.lab → 404
    - www.neduet.lab AAAA → 501
    - ping → PONG
3. In Wireshark use the filter `udp.port == 5400` to see the packets.

## AI assistance

Claude AI was used to help diagnose bugs in the programs and test scripts, explain error messages and Wireshark output. The declaration is in Appendix A of the report.
