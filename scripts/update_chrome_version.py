#!/usr/bin/env python3
"""Refresh src/fpforge/data/chrome-stable.json from Chrome for Testing.

    python scripts/update_chrome_version.py

Chrome's reduced User-Agent only exposes the major version, but the client
hints (`userAgentData.fullVersionList`) carry the full version, so the bundled
"stable" version should follow Chrome's release cadence (every ~4 weeks).
Source: https://googlechromelabs.github.io/chrome-for-testing/ (official, by the Chrome team).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Optional

URL = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"
TARGET = Path(__file__).resolve().parents[1] / "src" / "fpforge" / "data" / "chrome-stable.json"


def parse(payload: Mapping[str, Any]) -> str:
    """Extract the Stable channel version from the Chrome for Testing payload."""
    try:
        version = payload["channels"]["Stable"]["version"]
    except (KeyError, TypeError):
        raise ValueError("payload has no channels.Stable.version")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", str(version)):
        raise ValueError("unexpected version string: %r" % (version,))
    return str(version)


def write(path: Path, version: str, source: str, today: Optional[str] = None) -> None:
    data = {
        "version": version,
        "source": source,
        "retrieved": today or datetime.date.today().isoformat(),
    }
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=URL)
    ap.add_argument("--target", type=Path, default=TARGET)
    args = ap.parse_args()
    with urllib.request.urlopen(args.url, timeout=30) as resp:  # noqa: S310 (fixed https URL)
        version = parse(json.load(resp))
    write(args.target, version, args.url)
    print("chrome stable = %s -> %s" % (version, args.target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
