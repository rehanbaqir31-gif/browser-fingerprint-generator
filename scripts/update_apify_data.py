#!/usr/bin/env python3
"""Refresh the bundled Apify network files from github.com/apify/fingerprint-suite.

    python scripts/update_apify_data.py [--ref master]

Downloads the five data files, checks that each one parses, replaces them in
src/fpforge/data/ and prints their SHA-256 so DATA_SOURCES.md can be updated.
Run the test suite afterwards: the sampler and the version rewrite are tested
against the data itself.

The upstream paths below were taken from the repository layout at the time of
writing; if upstream moves a file this script fails loudly instead of guessing.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

RAW = "https://raw.githubusercontent.com/apify/fingerprint-suite/%s/packages/%s/src/data_files/%s"
FILES = [
    ("fingerprint-generator", "fingerprint-network-definition.zip"),
    ("header-generator", "header-network-definition.zip"),
    ("header-generator", "input-network-definition.zip"),
    ("header-generator", "headers-order.json"),
    ("header-generator", "browser-helper-file.json"),
]
DATA_DIR = Path(__file__).resolve().parents[1] / "src" / "fpforge" / "data"


def validate(name: str, blob: bytes) -> str:
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            nodes = json.loads(z.read(z.namelist()[0]))["nodes"]
        return "%d nodes" % len(nodes)
    json.loads(blob)
    return "valid JSON"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ref", default="master", help="git ref (branch, tag or commit) to download")
    args = ap.parse_args()
    downloaded = {}
    for package, name in FILES:
        url = RAW % (args.ref, package, name)
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (fixed https URL)
            blob = resp.read()
        info = validate(name, blob)
        downloaded[name] = blob
        print("%-42s %9d bytes  %s  sha256 %s" % (name, len(blob), info, hashlib.sha256(blob).hexdigest()))
    for name, blob in downloaded.items():  # only write once everything downloaded and parsed
        (DATA_DIR / name).write_bytes(blob)
    print("updated %d files in %s (ref %s)" % (len(downloaded), DATA_DIR, args.ref))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
