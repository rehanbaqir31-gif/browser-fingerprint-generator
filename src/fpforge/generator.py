"""Fingerprint profile generator backed by Apify's trained network.

Everything about the device (user agent, GPU, screen, fonts, cores, memory,
client hints, codecs, battery, media devices, ...) is sampled jointly from the
bundled ``fingerprint-network-definition.zip``, so the combination is one that
real browsers actually produce. Only locale/timezone come from
:mod:`fpforge.locale_data`, because the dataset does not contain them.
"""
from __future__ import annotations

import hashlib
import json
import random
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ._paths import DATA_DIR
from ._version import __version__
from .locale_data import fallback_locale, locale_for
from .network import BayesianNetwork
from .versions import load_chrome_stable, retarget_chrome

STRINGIFIED = "*STRINGIFIED*"
MISSING = "*MISSING_VALUE*"
SCHEMA_VERSION = 1

DESKTOP_OS = ("windows", "macos", "linux")
BROWSERS = ("chrome", "edge", "firefox", "safari")

# Renderers of VMs, remote desktops and headless setups: real, but they stand out.
SOFTWARE_GPU_MARKERS = ("Basic Render Driver", "Microsoft Basic", "SwiftShader", "llvmpipe", "softpipe")

# Desktop platforms. The dataset also holds Android phones in "desktop site" mode
# (platform "Linux armv81", Adreno/Mali GPUs); those are real but not desktops.
DESKTOP_PLATFORMS = frozenset({"Win32", "MacIntel", "Linux x86_64"})

# GPUs of ARM phone/tablet SoCs. Some records pair them with an x86 desktop platform
# string (spoofed or desktop-mode browsers); that is not a combination real desktops produce.
MOBILE_GPU_MARKERS = ("Adreno", "Mali", "PowerVR", "Immortalis")

# The dataset contains records from privacy extensions that randomise plugin names.
KNOWN_PDF_PLUGINS = frozenset(
    {
        "PDF Viewer",
        "Chrome PDF Viewer",
        "Chromium PDF Viewer",
        "Microsoft Edge PDF Viewer",
        "WebKit built-in PDF",
    }
)


class NoMatchingFingerprint(ValueError):
    """No fingerprint in the dataset matches the requested OS/browser."""


def decode(value: Any) -> Any:
    """Decode the dataset's ``*STRINGIFIED*`` / ``*MISSING_VALUE*`` encoding."""
    if value == MISSING:
        return None
    if isinstance(value, str) and value.startswith(STRINGIFIED):
        return json.loads(value[len(STRINGIFIED):])
    return value


def classify_user_agent(user_agent: str) -> Tuple[Optional[str], Optional[str]]:
    """(os, browser) of a desktop user agent, or (None, None) for mobile/unknown."""
    if any(m in user_agent for m in ("Android", "iPhone", "iPad", "Mobile", "CrOS")):
        return None, None
    if "Windows" in user_agent:
        os_name = "windows"
    elif "Macintosh" in user_agent:
        os_name = "macos"
    elif "X11" in user_agent and "Linux" in user_agent:
        os_name = "linux"
    else:
        return None, None
    if "Firefox/" in user_agent:
        browser = "firefox"
    elif "Edg/" in user_agent:
        browser = "edge"
    elif "OPR/" in user_agent or "YaBrowser" in user_agent or "Vivaldi" in user_agent:
        browser = "other"
    elif "Chrome/" in user_agent:
        browser = "chrome"
    elif "Safari/" in user_agent:
        browser = "safari"
    else:
        browser = "other"
    return os_name, browser


def _canonical_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


class FingerprintGenerator:
    """Generate consistent desktop browser fingerprint profiles.

    >>> gen = FingerprintGenerator()
    >>> profile = gen.generate(os="windows", browser="chrome", country="DE", seed="demo")
    """

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        network_path = self.data_dir / "fingerprint-network-definition.zip"
        self.network = BayesianNetwork(network_path)
        self.dataset_id = hashlib.sha256(network_path.read_bytes()).hexdigest()[:12]
        self._user_agents: Dict[Tuple[str, str], List[str]] = {}
        for ua in self.network.by_name["userAgent"]["possibleValues"]:
            os_name, browser = classify_user_agent(ua)
            if os_name and browser in BROWSERS:
                self._user_agents.setdefault((os_name, browser), []).append(ua)

    # ------------------------------------------------------------------ queries
    def available(self) -> Dict[Tuple[str, str], int]:
        """Number of distinct user agents in the dataset per (os, browser)."""
        return {k: len(v) for k, v in sorted(self._user_agents.items())}

    def _candidates(self, os_name: str, browser: str) -> List[str]:
        out: List[str] = []
        for (o, b), uas in self._user_agents.items():
            if os_name in ("any", o) and browser in ("any", b):
                out.extend(uas)
        return out

    # --------------------------------------------------------------- generation
    def generate(
        self,
        os: str = "windows",
        browser: str = "chrome",
        country: Optional[str] = None,
        *,
        chrome_full: Optional[str] = "auto",
        allow_software_gpu: bool = False,
        seed: Optional[Union[str, int]] = None,
        rng: Optional[random.Random] = None,
        max_attempts: int = 200,
    ) -> Dict[str, Any]:
        """Generate one profile.

        :param os: ``windows``, ``macos``, ``linux`` or ``any``.
        :param browser: ``chrome``, ``edge``, ``firefox``, ``safari`` or ``any``.
        :param country: ISO alpha-2 code of the proxy exit country; sets timezone
            and languages. Without it a small fallback pool is used.
        :param chrome_full: rewrite Chrome profiles to this full version.
            ``"auto"`` uses the bundled stable version, ``None`` keeps the
            dataset's own (older) versions.
        :param allow_software_gpu: keep VM / remote-desktop renderers.
        :param seed: makes the result reproducible (same Python version).
        """
        if os not in DESKTOP_OS + ("any",):
            raise ValueError("os must be one of %s or 'any'" % (DESKTOP_OS,))
        if browser not in BROWSERS + ("any",):
            raise ValueError("browser must be one of %s or 'any'" % (BROWSERS,))
        candidates = self._candidates(os, browser)
        if not candidates:
            raise NoMatchingFingerprint("no %s/%s fingerprints in the dataset" % (os, browser))
        rng = rng or random.Random(seed)
        if chrome_full == "auto":
            chrome_full = load_chrome_stable(self.data_dir)

        for _ in range(max_attempts):
            raw = self.network.generate_consistent_sample(rng, {"userAgent": candidates})
            if raw is None:
                raise NoMatchingFingerprint("no consistent sample for %s/%s" % (os, browser))
            data = {k: decode(v) for k, v in raw.items()}
            if self._acceptable(data, allow_software_gpu):
                break
        else:
            raise RuntimeError("could not sample an acceptable fingerprint in %d attempts" % max_attempts)

        profile = self._build_profile(data, country, rng)
        if chrome_full and profile["browser"] == "chrome":
            profile = retarget_chrome(profile, chrome_full)
        return profile

    def generate_many(
        self, count: int, *, seed: Optional[Union[str, int]] = None, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Generate ``count`` profiles; with a seed the whole list is reproducible."""
        out = []
        for i in range(count):
            rng = random.Random("%s-%d" % (seed, i)) if seed is not None else random.Random()
            out.append(self.generate(rng=rng, **kwargs))
        return out

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _acceptable(data: Dict[str, Any], allow_software_gpu: bool) -> bool:
        if data.get("platform") not in DESKTOP_PLATFORMS:
            return False
        video = data.get("videoCard") or {}
        renderer = video.get("renderer") or ""
        if not renderer or not video.get("vendor"):
            return False  # a profile without a GPU would show the real WebGL renderer
        if any(m in renderer for m in MOBILE_GPU_MARKERS):
            return False
        if not allow_software_gpu and any(m in renderer for m in SOFTWARE_GPU_MARKERS):
            return False
        plugins = (data.get("pluginsData") or {}).get("plugins") or []
        if any(p.get("name") not in KNOWN_PDF_PLUGINS for p in plugins):
            return False
        return bool(data.get("fonts")) and bool(data.get("screen"))

    def _build_profile(self, d: Dict[str, Any], country: Optional[str], rng: random.Random) -> Dict[str, Any]:
        os_name, browser = classify_user_agent(d["userAgent"])
        if country:
            languages, timezone, accept_language = locale_for(country, rng)
            country = country.upper()
        else:
            languages, timezone, accept_language = fallback_locale(rng)
        video = d.get("videoCard") or {}
        profile: Dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "os": os_name,
            "browser": browser,
            "userAgent": d["userAgent"],
            "platform": d["platform"],
            "appVersion": d.get("appVersion"),
            "vendor": d.get("vendor"),
            "productSub": d.get("productSub"),
            "oscpu": d.get("oscpu"),
            "userAgentData": d.get("userAgentData"),
            "hardwareConcurrency": d.get("hardwareConcurrency"),
            "deviceMemory": d.get("deviceMemory"),
            "maxTouchPoints": d.get("maxTouchPoints"),
            "doNotTrack": d.get("doNotTrack"),
            "webdriver": False,
            "language": languages[0],
            "languages": languages,
            "acceptLanguage": accept_language,
            "timezone": timezone,
            "country": country,
            "screen": d["screen"],
            "webgl": {
                "vendor": "WebKit",
                "renderer": "WebKit WebGL",
                "unmaskedVendor": video.get("vendor"),
                "unmaskedRenderer": video.get("renderer"),
            },
            "canvas": {"mode": "noise", "noiseSeed": rng.getrandbits(32)},
            "audio": {"mode": "noise", "noiseSeed": rng.getrandbits(32), "codecs": d.get("audioCodecs")},
            "videoCodecs": d.get("videoCodecs"),
            "fonts": d["fonts"],
            "plugins": d.get("pluginsData"),
            "battery": d.get("battery"),
            "mediaDevices": d.get("multimediaDevices"),
            "extraProperties": d.get("extraProperties"),
            "webrtc": {"mode": "altered"},
        }
        profile["fingerprintId"] = _canonical_hash(profile)[:32]
        profile["profileUuid"] = str(uuid.UUID(int=rng.getrandbits(128), version=4))
        profile["meta"] = {"generator": "fpforge", "version": __version__, "dataset": self.dataset_id}
        return profile


def generate_profile(**kwargs: Any) -> Dict[str, Any]:
    """Convenience wrapper: ``generate_profile(os="macos", country="US")``."""
    return FingerprintGenerator().generate(**kwargs)
