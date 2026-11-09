"""HTTP request headers that match a fingerprint profile.

For plain HTTP clients (``requests``, ``httpx``, ...). A real browser driven by
Playwright already sends correct headers by itself, so the injector does not
use this module.

``Accept``, ``Accept-Encoding``, ``Upgrade-Insecure-Requests``, ``DNT`` etc. are
sampled from Apify's header network (real browser traffic), constrained to the
profile's browser and OS. The values that must agree with ``navigator`` are
taken from the profile itself: ``User-Agent``, ``sec-ch-ua*`` and
``Accept-Language``. Header order follows ``headers-order.json``.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from ._paths import DATA_DIR
from .network import BayesianNetwork

MISSING = "*MISSING_VALUE*"

_SEC_FETCH = {
    "2": {"site": "sec-fetch-site", "mode": "sec-fetch-mode", "user": "sec-fetch-user", "dest": "sec-fetch-dest"},
    "1": {"site": "Sec-Fetch-Site", "mode": "Sec-Fetch-Mode", "user": "Sec-Fetch-User", "dest": "Sec-Fetch-Dest"},
}
_VERSION_RES = {
    "chrome": re.compile(r"Chrome/(\d+)"),
    "edge": re.compile(r"Edg/(\d+)"),
    "firefox": re.compile(r"Firefox/(\d+)"),
    "safari": re.compile(r"Version/(\d+)"),
}
_SEC_FETCH_MIN = {"chrome": 76, "edge": 79, "firefox": 90}


def _header_name(name: str, http_version: str) -> str:
    """HTTP/2 uses lower-case names; HTTP/1.1 uses Pascal-Case (Apify convention)."""
    if http_version == "2" or name.startswith("sec-ch-ua"):
        return name.lower()
    if name.lower() in ("dnt", "rtt", "ect"):
        return name.upper()
    return "-".join(part.capitalize() for part in name.split("-"))


class HeaderGenerator:
    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        d = Path(data_dir) if data_dir else DATA_DIR
        self.input_network = BayesianNetwork(d / "input-network-definition.zip")
        self.header_network = BayesianNetwork(d / "header-network-definition.zip")
        self.order: Dict[str, List[str]] = json.loads((d / "headers-order.json").read_text())
        self._browsers: List[Tuple[str, int, str, str]] = []  # (name, major, http, full string)
        for s in json.loads((d / "browser-helper-file.json").read_text()):
            if s == MISSING:
                continue
            browser_part, _, http = s.partition("|")
            name, _, version = browser_part.partition("/")
            self._browsers.append((name, int(version.split(".")[0]), http, s))

    # ------------------------------------------------------------------ helpers
    def _candidates(self, browser: str, major: int, http_version: str) -> List[str]:
        same = [(abs(m - major), m, s) for n, m, h, s in self._browsers if n == browser and h == http_version]
        if not same:
            return []
        best = min(d for d, _, _ in same)
        return [s for d, _, s in same if d == best]

    @staticmethod
    def _profile_major(profile: Mapping[str, Any]) -> int:
        rx = _VERSION_RES.get(profile["browser"])
        m = rx.search(profile["userAgent"]) if rx else None
        return int(m.group(1)) if m else 0

    def _order(self, headers: Dict[str, str], browser: str) -> Dict[str, str]:
        order = self.order.get(browser, [])
        out = {k: headers[k] for k in order if k in headers}
        out.update({k: v for k, v in headers.items() if k not in out})
        return out

    # --------------------------------------------------------------- generation
    def generate(
        self,
        profile: Mapping[str, Any],
        *,
        http_version: str = "2",
        sec_fetch_site: str = "none",
        extra: Optional[Mapping[str, str]] = None,
        seed: Optional[Union[str, int]] = None,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, str]:
        """Headers for a top-level navigation request made by ``profile``.

        ``sec_fetch_site`` defaults to ``none`` (a user typing the URL); use
        ``cross-site`` / ``same-origin`` etc. when simulating link clicks.
        """
        if http_version not in ("1", "2"):
            raise ValueError("http_version must be '1' or '2'")
        rng = rng or random.Random(seed)
        browser = profile["browser"]
        candidates = self._candidates(browser, self._profile_major(profile), http_version)
        if not candidates:
            raise ValueError("no %s headers for HTTP/%s in the dataset" % (browser, http_version))

        inputs = self.input_network.generate_consistent_sample(
            rng,
            {"*BROWSER_HTTP": candidates, "*OPERATING_SYSTEM": [profile["os"]], "*DEVICE": ["desktop"]},
        )
        if inputs is None:
            raise ValueError("no %s headers for %s in the dataset" % (browser, profile["os"]))
        sample = self.header_network.generate_sample(rng, inputs)

        headers: Dict[str, str] = {}
        for key, value in sample.items():
            if key.startswith("*") or value == MISSING:
                continue
            if key.lower() == "connection" and value == "close":
                continue
            headers[key] = value

        def name(n: str) -> str:
            return _header_name(n, http_version)

        headers[name("user-agent")] = profile["userAgent"]
        headers[name("accept-language")] = profile["acceptLanguage"]

        uad = profile.get("userAgentData")
        if uad and uad.get("brands") and name("sec-ch-ua") in headers:
            headers[name("sec-ch-ua")] = ", ".join(
                '"%s";v="%s"' % (b["brand"], b["version"]) for b in uad["brands"]
            )
            headers[name("sec-ch-ua-mobile")] = "?1" if uad.get("mobile") else "?0"
            headers[name("sec-ch-ua-platform")] = '"%s"' % uad.get("platform", "")

        if self._profile_major(profile) >= _SEC_FETCH_MIN.get(browser, 10 ** 9):
            sf = _SEC_FETCH[http_version]
            headers[sf["site"]] = sec_fetch_site
            headers[sf["mode"]] = "navigate"
            headers[sf["dest"]] = "document"
            headers[sf["user"]] = "?1"  # user-activated navigation

        headers.update(extra or {})
        return self._order(headers, browser)
