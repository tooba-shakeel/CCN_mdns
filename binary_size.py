"""
binary_size.py - compare the size of MDNS/1.0 text messages with an equivalent binary format.
Used for the design tension "Compactness vs readability" (report Section 7.1).

Run:  py binary_size.py
"""
import socket
import struct
from common import build

HEADERS = 14 + 20 + 8          # Ethernet + IP + UDP header bytes added to every packet

name = "www.neduet.lab"

# ---- text messages, built exactly as our programs send them
text_query = build("QUERY", {"ID": 36387, "NAME": name, "RTYPE": "A"})
text_response = build("RESPONSE", {"ID": 36387, "NAME": name, "RTYPE": "A", "STATUS": 200,
                                   "TTL": 60, "SRC": "AUTH", "VALUE": "10.0.0.5"})

# ---- the same information packed as binary
#   ID 2 bytes, message type 1 byte, RTYPE 1 byte, name length 1 byte + name
#   response adds: STATUS 1 byte, TTL 4 bytes, SRC 1 byte, IPv4 VALUE 4 bytes
n = name.encode("ascii")
binary_query = struct.pack("!HBBB", 36387, 1, 1, len(n)) + n
binary_response = (struct.pack("!HBBB", 36387, 2, 1, len(n)) + n
                   + struct.pack("!BIB", 200, 60, 1)        # STATUS (200 fits in 1 byte), TTL, SRC (1 = AUTH)
                   + socket.inet_aton("10.0.0.5"))          # IPv4 address as 4 bytes

print(f"{'Message':<10}{'Text':>8}{'Binary':>8}{'Packet text':>13}{'Packet binary':>15}")
for label, t, b in (("QUERY", text_query, binary_query), ("RESPONSE", text_response, binary_response)):
    print(f"{label:<10}{len(t):>8}{len(b):>8}{len(t) + HEADERS:>13}{len(b) + HEADERS:>15}")

total_t = len(text_query) + len(text_response)
total_b = len(binary_query) + len(binary_response)
saving = 1 - (total_b + 2 * HEADERS) / (total_t + 2 * HEADERS)
print(f"{'Lookup':<10}{total_t:>8}{total_b:>8}{total_t + 2 * HEADERS:>13}{total_b + 2 * HEADERS:>15}")
print(f"\nText is {total_t / total_b:.1f} times larger; binary would save {saving:.0%} per lookup on the wire.")
print("\nBinary QUERY bytes (not human-readable):", binary_query.hex(" "))
print("Text QUERY (readable):", text_query)
