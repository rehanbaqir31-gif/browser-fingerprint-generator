"""Matching HTTP headers for plain HTTP clients (no browser).

    python examples/http_requests.py                        # print the headers
    python examples/http_requests.py --send https://example.com
"""
import argparse
import urllib.request

from fpforge import FingerprintGenerator, HeaderGenerator

ap = argparse.ArgumentParser()
ap.add_argument("--send", metavar="URL")
args = ap.parse_args()

profile = FingerprintGenerator().generate(os="windows", browser="chrome", country="US")
headers = HeaderGenerator().generate(profile, http_version="1")
for k, v in headers.items():
    print("%s: %s" % (k, v))

if args.send:
    # urllib speaks HTTP/1.1 and handles gzip itself only if asked: drop Accept-Encoding for simplicity
    headers.pop("Accept-Encoding", None)
    req = urllib.request.Request(args.send, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.status, len(resp.read()), "bytes")
