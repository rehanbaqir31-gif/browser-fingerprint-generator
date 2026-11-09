"""Chrome version handling.

The bundled Apify dataset is a snapshot, so its Chrome entries lag behind the
current stable release. ``retarget_chrome`` rewrites a finished Chrome profile
to a newer Chrome build: the user agent, ``appVersion`` and the client hints.

The only non-trivial part is the GREASE brand in ``navigator.userAgentData``
(the fake ``Not?A_Brand`` entry). Chromium derives its name, version and its
position in the brand list from the major version. The rules below were
reverse-engineered from the dataset itself and are checked against it in the
test suite (they match 978 of 993 brand lists in the bundled snapshot).
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ._paths import DATA_DIR

GREASE_CHARS = [" ", "(", ":", "-", ".", "/", ")", ";", "=", "?", "_"]
GREASE_VERSIONS = ["8", "99", "24"]
# Brand order by major % 6. G = GREASE brand, B = "Google Chrome", C = "Chromium".
BRAND_ORDERS = {0: "GCB", 1: "GBC", 2: "CGB", 3: "BGC", 4: "CBG", 5: "BCG"}

FALLBACK_CHROME_FULL = "157.0.8103.38"
_CHROME_RE = re.compile(r"Chrome/\d+\.0\.0\.0")


def grease_brand(major: int) -> Tuple[str, str]:
    """(brand name, version) of the GREASE entry for a Chrome major version."""
    name = "Not%sA%sBrand" % (GREASE_CHARS[major % 11], GREASE_CHARS[(major + 1) % 11])
    return name, GREASE_VERSIONS[major % 3]


def chrome_brands(major: int, full_version: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """(brands, fullVersionList) as exposed by ``navigator.userAgentData``."""
    g_name, g_ver = grease_brand(major)
    short = {"G": (g_name, g_ver), "B": ("Google Chrome", str(major)), "C": ("Chromium", str(major))}
    full = {
        "G": (g_name, g_ver + ".0.0.0"),
        "B": ("Google Chrome", full_version),
        "C": ("Chromium", full_version),
    }
    order = BRAND_ORDERS[major % 6]
    return (
        [{"brand": short[c][0], "version": short[c][1]} for c in order],
        [{"brand": full[c][0], "version": full[c][1]} for c in order],
    )


def major_of(version: str) -> int:
    return int(version.split(".")[0])


def load_chrome_stable(data_dir: Optional[Union[str, Path]] = None) -> str:
    """Full version string of the bundled Chrome stable (``chrome-stable.json``)."""
    path = Path(data_dir or DATA_DIR) / "chrome-stable.json"
    try:
        return str(json.loads(path.read_text())["version"])
    except (OSError, ValueError, KeyError):
        return FALLBACK_CHROME_FULL


def retarget_chrome(profile: Dict[str, Any], chrome_full: str) -> Dict[str, Any]:
    """Return a copy of ``profile`` rewritten to Chrome ``chrome_full``.

    Only plain Chrome profiles are touched (Edge, Firefox and Safari are
    returned unchanged), because the full version of those browsers is not
    known here.
    """
    out = copy.deepcopy(profile)
    if out.get("browser") != "chrome":
        return out
    major = major_of(chrome_full)
    out["userAgent"] = _CHROME_RE.sub("Chrome/%d.0.0.0" % major, out["userAgent"])
    if isinstance(out.get("appVersion"), str):
        out["appVersion"] = _CHROME_RE.sub("Chrome/%d.0.0.0" % major, out["appVersion"])
    uad = out.get("userAgentData")
    if isinstance(uad, dict) and uad.get("brands"):
        uad["brands"], full_list = chrome_brands(major, chrome_full)
        if "fullVersionList" in uad:
            uad["fullVersionList"] = full_list
        if "uaFullVersion" in uad:
            uad["uaFullVersion"] = chrome_full
    meta = out.setdefault("meta", {})
    meta["chromeFullVersion"] = chrome_full
    return out
