"""Playwright-independent half of the injector.

Everything here is a pure function of a profile, so it is unit-testable without
a browser. The sync and async wrappers only orchestrate Playwright calls.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union
from urllib.parse import unquote, urlsplit

from ..versions import major_of, retarget_chrome

INJECT_JS = Path(__file__).with_name("inject.js")
SUPPORTED_BROWSERS = ("chrome", "edge")  # the injector drives Chromium
IGNORE_DEFAULT_ARGS = ["--enable-automation"]  # sets navigator.webdriver and shows an infobar

# Approximate height of tab strip + toolbar, to derive innerHeight from outerHeight.
BROWSER_UI_HEIGHT = {"windows": 87, "macos": 79, "linux": 85}

ProxyLike = Union[None, str, Mapping[str, str]]


class UnsupportedProfile(ValueError):
    """The profile cannot be applied by a Chromium-based injector."""


def check_supported(profile: Mapping[str, Any]) -> None:
    if profile.get("browser") not in SUPPORTED_BROWSERS:
        raise UnsupportedProfile(
            "the injector drives Chromium and supports %s profiles, not %r. "
            "Generate one with browser='chrome' or browser='edge'."
            % (SUPPORTED_BROWSERS, profile.get("browser"))
        )


def match_engine_version(profile: Dict[str, Any], engine_version: str) -> Dict[str, Any]:
    """Make the profile's browser version equal the real engine's version.

    A page can probe engine features, so claiming a Chrome version that the
    running binary does not have is a detectable mismatch. Chrome profiles are
    rewritten to the real version; Edge profiles cannot be (their Edge build
    number is unknown) and only trigger a warning.
    """
    if profile["browser"] == "chrome":
        return retarget_chrome(profile, engine_version)
    claimed = _claimed_major(profile)
    if claimed != major_of(engine_version):
        warnings.warn(
            "profile claims Edge %s but the running Chromium is %s; engine and "
            "claimed version differ" % (claimed, engine_version),
            stacklevel=3,
        )
    return profile


def _claimed_major(profile: Mapping[str, Any]) -> int:
    import re

    m = re.search(r"(?:Chrome|Edg)/(\d+)", profile["userAgent"])
    return int(m.group(1)) if m else 0


def normalize_proxy(proxy: ProxyLike) -> Optional[Dict[str, str]]:
    """Accept ``"http://user:pass@host:port"`` or a Playwright proxy dict.

    Playwright wants credentials as separate keys, so they are split off the URL.
    """
    if not proxy:
        return None
    if not isinstance(proxy, str):
        return dict(proxy)
    parts = urlsplit(proxy)
    if not parts.username:
        return {"server": proxy}
    host = parts.hostname or ""
    if ":" in host:  # IPv6 literal
        host = "[%s]" % host
    server = "%s://%s%s" % (parts.scheme, host, ":%d" % parts.port if parts.port else "")
    out = {"server": server, "username": unquote(parts.username)}
    if parts.password is not None:
        out["password"] = unquote(parts.password)
    return out


# --------------------------------------------------------------------- page side
def js_config(profile: Mapping[str, Any]) -> Dict[str, Any]:
    """The subset of the profile that the page-side script needs."""
    screen = profile.get("screen") or {}
    media = profile.get("mediaDevices")
    return {
        "platform": profile.get("platform"),
        "vendor": profile.get("vendor"),
        "hardwareConcurrency": profile.get("hardwareConcurrency"),
        "deviceMemory": profile.get("deviceMemory"),
        "maxTouchPoints": profile.get("maxTouchPoints"),
        "doNotTrack": profile.get("doNotTrack"),
        "languages": profile.get("languages"),
        "screen": {
            k: screen.get(k)
            for k in (
                "width", "height", "availWidth", "availHeight", "availLeft", "availTop",
                "colorDepth", "pixelDepth", "outerWidth", "outerHeight", "devicePixelRatio",
            )
        },
        "webgl": profile.get("webgl"),
        "canvas": profile.get("canvas"),
        "audio": {k: v for k, v in (profile.get("audio") or {}).items() if k != "codecs"},
        "battery": profile.get("battery"),
        "mediaDevices": media,
        "webrtc": profile.get("webrtc"),
    }


def init_script(profile: Mapping[str, Any]) -> str:
    """JavaScript source for ``context.add_init_script``."""
    source = INJECT_JS.read_text(encoding="utf-8").rstrip().rstrip(";")
    return "%s(%s);" % (source, json.dumps(js_config(profile)))


# --------------------------------------------------------------------- CDP side
def cdp_user_agent_override(profile: Mapping[str, Any]) -> Dict[str, Any]:
    """Parameters for ``Emulation.setUserAgentOverride``.

    This sets the User-Agent and Accept-Language request headers, the
    ``sec-ch-ua*`` client-hint headers and ``navigator.userAgentData`` in one
    go, so the network layer and JavaScript cannot disagree.
    """
    params: Dict[str, Any] = {
        "userAgent": profile["userAgent"],
        # a plain list: Chrome derives the ";q=" weights itself and would double them
        "acceptLanguage": ",".join(profile["languages"]),
        "platform": profile["platform"],
    }
    uad = profile.get("userAgentData")
    if uad and uad.get("brands"):
        params["userAgentMetadata"] = {
            "brands": uad["brands"],
            "fullVersionList": uad.get("fullVersionList") or uad["brands"],
            "fullVersion": uad.get("uaFullVersion", ""),
            "platform": uad.get("platform", ""),
            "platformVersion": uad.get("platformVersion", ""),
            "architecture": uad.get("architecture", ""),
            "model": uad.get("model", ""),
            "mobile": bool(uad.get("mobile", False)),
            "bitness": uad.get("bitness", ""),
            "wow64": False,
        }
    return params


# ------------------------------------------------------------------- workers
# A page-level CDP session can auto-attach to the page's dedicated workers and keep
# each one paused at its first instruction. We evaluate the same script in it, then
# resume it, so worker code never observes the real navigator values.
AUTO_ATTACH_WORKERS = {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": False}
WORKER_TARGET_TYPES = ("worker",)


def target_message(message_id: int, method: str, params: Optional[Mapping[str, Any]] = None) -> str:
    """JSON payload for ``Target.sendMessageToTarget`` (non-flattened child sessions)."""
    return json.dumps({"id": message_id, "method": method, "params": dict(params or {})})


def worker_setup_messages(profile: Mapping[str, Any]) -> List[str]:
    """Messages to send to a freshly attached, paused worker, in order."""
    return [
        target_message(1, "Runtime.evaluate", {"expression": init_script(profile), "silent": True}),
        target_message(2, "Runtime.runIfWaitingForDebugger"),
    ]


# --------------------------------------------------------------- Playwright options
def context_options(profile: Mapping[str, Any]) -> Dict[str, Any]:
    """Keyword arguments for ``browser.new_context`` / ``launch_persistent_context``.

    ``user_agent`` is passed so that even the first request of a popup carries
    the right User-Agent; the injector then replaces Playwright's client-hint
    metadata through CDP (``cdp_user_agent_override``).
    """
    screen = profile["screen"]
    width, height = int(screen["width"]), int(screen["height"])
    outer_w = int(screen.get("outerWidth") or width)
    outer_h = int(screen.get("outerHeight") or screen.get("availHeight") or height)
    ui = BROWSER_UI_HEIGHT.get(profile["os"], 85)
    return {
        "user_agent": profile["userAgent"],
        "locale": profile["language"],
        "timezone_id": profile["timezone"],
        "viewport": {"width": min(outer_w, width), "height": max(outer_h - ui, 200)},
        "screen": {"width": width, "height": height},
        "device_scale_factor": round(float(screen.get("devicePixelRatio") or 1), 2),
        "is_mobile": False,
        "has_touch": bool(profile.get("maxTouchPoints")),
        # sent from the very first request, including popups, before CDP overrides land
        "extra_http_headers": {"Accept-Language": profile["acceptLanguage"]},
    }


def launch_args(profile: Mapping[str, Any]) -> List[str]:
    args = ["--disable-blink-features=AutomationControlled"]
    mode = (profile.get("webrtc") or {}).get("mode", "altered")
    if mode in ("altered", "disabled"):
        # never reveal the local/real IP through WebRTC; only proxied UDP is allowed
        args.append("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
        args.append("--webrtc-ip-handling-policy=disable_non_proxied_udp")
    return args
