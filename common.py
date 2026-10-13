"""
common.py - shared code for MDNS/1.0 (used by client, resolver and auth server).
Message layout
    MDNS/1.0 <TYPE>\r\n
    <Field>: <value>\r\n
    ...
    \r\n
"""
import os
import time
HERE = os.path.dirname(os.path.abspath(__file__))   # folder holding these files (works on phones too)

VERSION = "MDNS/1.0"
MAX_SIZE = 1024                       # bytes, one message per UDP datagram

MESSAGE_TYPES = ("QUERY", "RESPONSE", "PING", "PONG", "FLUSH")
RECORD_TYPES = ("A", "CNAME", "MX")
RESOLVER_PORT = 5300
AUTH_PORT = 5400


def build(msg_type, headers):
    #Turn a message type and a dict of headers into bytes ready to send.
    lines = [f"{VERSION} {msg_type}"]
    for field, value in headers.items():
        lines.append(f"{field}: {value}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
def parse(data):
    """
    Turn received bytes back into (msg_type, headers).
    Raises ValueError for anything that breaks the format rules then caller replies 400.
    """
    if len(data) > MAX_SIZE:
        raise ValueError("message too long")
    text = data.decode("ascii")                 # UnicodeDecodeError is a ValueError
    if not text.endswith("\r\n\r\n"):
        raise ValueError("missing empty line at end")

    lines = text[:-4].split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 2 or parts[0] != VERSION:
        raise ValueError("bad start line")
    msg_type = parts[1]

    headers = {}
    for line in lines[1:]:
        if ": " not in line:
            raise ValueError(f"bad header line: {line!r}")
        field, value = line.split(": ", 1)
        if field in headers:
            raise ValueError(f"duplicate field: {field}")
        headers[field] = value
    return msg_type, headers

def require(headers, *fields):
    #Raise ValueError if any required field is missing then caller replies 400.
    missing = [f for f in fields if f not in headers]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")
def log(role, text):
    #Timestamped log line to the screen and to <role>.log
    line = f"{time.time():.6f} [{role}] {text}"
    print(line, flush=True)
    try:
        with open(os.path.join(HERE, f"{role.lower()}.log"), "a") as f:
            f.write(line + "\n")
    except OSError:
        pass                                    # e.g. read-only folder on a phone: keep running
