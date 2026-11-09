"""Command line interface: ``fpforge generate | headers | info``."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

from ._version import __version__
from .generator import BROWSERS, DESKTOP_OS, FingerprintGenerator, NoMatchingFingerprint
from .headers import HeaderGenerator
from .locale_data import COUNTRY_TIMEZONES
from .versions import load_chrome_stable


def _country(value: str) -> str:
    value = value.upper()
    if value not in COUNTRY_TIMEZONES:
        raise argparse.ArgumentTypeError("unknown ISO country code: %s" % value)
    return value


def _add_generation_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--os", choices=DESKTOP_OS + ("any",), default="windows")
    p.add_argument("--browser", choices=BROWSERS + ("any",), default="chrome")
    p.add_argument("--country", type=_country, help="proxy exit country (ISO alpha-2) for timezone/languages")
    p.add_argument("--chrome-full", help="rewrite Chrome profiles to this full version (default: bundled stable)")
    p.add_argument("--no-retarget", action="store_true", help="keep the dataset's own, older Chrome versions")
    p.add_argument("--allow-software-gpu", action="store_true", help="keep VM/RDP/headless GPU renderers")
    p.add_argument("--seed", help="reproducible output")


def _gen_kwargs(a: argparse.Namespace) -> dict:
    chrome_full = None if a.no_retarget else (a.chrome_full or "auto")
    return dict(
        os=a.os,
        browser=a.browser,
        country=a.country,
        chrome_full=chrome_full,
        allow_software_gpu=a.allow_software_gpu,
    )


def _write(text: str, output: Optional[str]) -> None:
    if output:
        Path(output).write_text(text + "\n")
        print("wrote %s" % output, file=sys.stderr)
    else:
        print(text)


def cmd_generate(a: argparse.Namespace) -> int:
    gen = FingerprintGenerator()
    profiles = gen.generate_many(a.count, seed=a.seed, **_gen_kwargs(a))
    data = profiles if (a.count > 1 or a.array) else profiles[0]
    _write(json.dumps(data, indent=None if a.compact else 2), a.output)
    return 0


def cmd_headers(a: argparse.Namespace) -> int:
    gen = FingerprintGenerator()
    profile = gen.generate_many(1, seed=a.seed, **_gen_kwargs(a))[0]
    headers = HeaderGenerator().generate(profile, http_version=a.http_version, seed=a.seed)
    _write(json.dumps(headers, indent=2), a.output)
    return 0


def cmd_launch(a: argparse.Namespace) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("error: Playwright is not installed.\n"
              "  pip install 'fpforge[playwright]' && playwright install chromium", file=sys.stderr)
        return 2
    from .injector.sync_api import launch_context

    data = json.loads(Path(a.profile).read_text())
    profile = data[a.index] if isinstance(data, list) else data
    with sync_playwright() as p:
        session = launch_context(
            p, profile, headless=a.headless, proxy=a.proxy,
            user_data_dir=a.user_data_dir, channel=a.channel,
        )
        try:
            page = session.new_page()
            if a.url:
                page.goto(a.url)
            if a.headless:
                time.sleep(a.wait)
            else:  # run until the user closes every window
                while session.context.pages:
                    session.context.pages[0].wait_for_event("close", timeout=0)
                    # a closed page is removed from the list before the next check
        finally:
            session.close()
    return 0


def cmd_info(a: argparse.Namespace) -> int:
    gen = FingerprintGenerator()
    print("fpforge %s" % __version__)
    print("dataset sha256[:12]: %s" % gen.dataset_id)
    print("bundled Chrome stable: %s" % load_chrome_stable())
    print("user agents per (os, browser) in the dataset:")
    for (os_name, browser), n in gen.available().items():
        print("  %-8s %-8s %d" % (os_name, browser, n))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fpforge", description=__doc__)
    p.add_argument("--version", action="version", version="fpforge " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate fingerprint profiles as JSON")
    _add_generation_args(g)
    g.add_argument("-n", "--count", type=int, default=1)
    g.add_argument("-o", "--output")
    g.add_argument("--compact", action="store_true", help="single-line JSON")
    g.add_argument("--array", action="store_true", help="always output a JSON array")
    g.set_defaults(func=cmd_generate)

    h = sub.add_parser("headers", help="generate a profile plus matching HTTP request headers")
    _add_generation_args(h)
    h.add_argument("--http-version", choices=["1", "2"], default="2")
    h.add_argument("-o", "--output")
    h.set_defaults(func=cmd_headers)

    la = sub.add_parser("launch", help="open Chromium with a saved profile (needs the playwright extra)")
    la.add_argument("profile", help="JSON file written by `fpforge generate`")
    la.add_argument("--index", type=int, default=0, help="which profile if the file holds a list")
    la.add_argument("--url", help="page to open")
    la.add_argument("--proxy", help="http://[user:pass@]host:port or socks5://host:port")
    la.add_argument("--user-data-dir", help="persistent browser profile directory (cookies, storage survive)")
    la.add_argument("--channel", help="Playwright channel, default chromium; 'chrome' for installed Google Chrome")
    la.add_argument("--headless", action="store_true")
    la.add_argument("--wait", type=float, default=2.0, help="seconds to stay open when headless")
    la.set_defaults(func=cmd_launch)

    i = sub.add_parser("info", help="show dataset and version information")
    i.set_defaults(func=cmd_info)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except NoMatchingFingerprint as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
