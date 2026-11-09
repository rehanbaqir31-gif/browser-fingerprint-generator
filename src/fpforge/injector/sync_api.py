"""Synchronous Playwright integration.

    from playwright.sync_api import sync_playwright
    from fpforge import FingerprintGenerator
    from fpforge.injector.sync_api import launch_context

    profile = FingerprintGenerator().generate(os="windows", country="DE")
    with sync_playwright() as p, launch_context(p, profile, headless=False) as session:
        page = session.new_page()
        page.goto("https://example.com")
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, List, Mapping, Optional, Set

from .core import (
    IGNORE_DEFAULT_ARGS,
    AUTO_ATTACH_WORKERS,
    ProxyLike,
    WORKER_TARGET_TYPES,
    cdp_user_agent_override,
    check_supported,
    context_options,
    init_script,
    launch_args,
    match_engine_version,
    normalize_proxy,
    worker_setup_messages,
)


class Session:
    """A browser context with a fingerprint profile applied."""

    def __init__(self, context: Any, browser: Any, profile: Dict[str, Any]):
        self.context = context
        self.browser = browser
        self.profile = profile

    def new_page(self) -> Any:
        return self.context.new_page()

    def close(self) -> None:
        self.context.close()
        if self.browser is not None:
            self.browser.close()

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _patch_workers(page: Any, cdp: Any, messages: List[str]) -> None:
    """Run the override script inside every dedicated worker before its own code starts.

    The auto-attach setting is lost when the page swaps its frame on navigation
    (about:blank -> site), so it is re-sent on every main-frame navigation.
    """
    patched: Set[str] = set()

    def on_attached(event: Any) -> None:
        sid = event["sessionId"]
        if event["targetInfo"]["type"] not in WORKER_TARGET_TYPES or sid in patched:
            return
        patched.add(sid)
        try:
            for message in messages:
                cdp.send("Target.sendMessageToTarget", {"sessionId": sid, "message": message})
        except Exception as exc:  # worker already gone
            warnings.warn("could not patch worker: %s" % exc)

    def attach(*_: Any) -> None:
        try:
            cdp.send("Target.setAutoAttach", AUTO_ATTACH_WORKERS)
        except Exception:  # page closed while navigating
            pass

    cdp.on("Target.attachedToTarget", on_attached)
    page.on("framenavigated", lambda frame: attach() if frame == page.main_frame else None)
    attach()


def apply_profile(context: Any, profile: Mapping[str, Any]) -> None:
    """Apply ``profile`` to an existing Chromium context (current and future pages).

    The profile is used as given; version matching is done by ``launch_context``.
    Browser-level options (viewport, locale, timezone, ...) are *not* set here;
    create the context with :func:`fpforge.injector.core.context_options`.
    """
    check_supported(profile)
    ua_params = cdp_user_agent_override(profile)
    worker_messages = worker_setup_messages(profile)
    context.add_init_script(init_script(profile))

    sessions: Dict[int, Any] = {}  # one CDP session per page, reused on re-apply

    def hook(page: Any) -> None:
        try:
            cdp = sessions.get(id(page))
            if cdp is None:
                cdp = sessions[id(page)] = context.new_cdp_session(page)
                page.once("close", lambda *_: sessions.pop(id(page), None))
                _patch_workers(page, cdp, worker_messages)
            cdp.send("Emulation.setUserAgentOverride", ua_params)
        except Exception as exc:  # page closed early, or not Chromium
            warnings.warn("could not apply user-agent override: %s" % exc)

    for page in list(context.pages):
        hook(page)

    # The "page" event can fire before Playwright finished its own page setup and
    # (in the sync API) after the first navigation was sent. Wrapping new_page()
    # applies the override once the page is ready, before the caller can
    # navigate; the event hook covers pages opened by scripts (popups).
    # Applying twice is harmless: the overrides are idempotent.
    original_new_page = context.new_page

    def new_page(*args: Any, **kwargs: Any) -> Any:
        page = original_new_page(*args, **kwargs)
        hook(page)
        return page

    context.new_page = new_page
    context.on("page", hook)


def launch_context(
    playwright: Any,
    profile: Mapping[str, Any],
    *,
    headless: bool = True,
    proxy: ProxyLike = None,
    user_data_dir: Optional[str] = None,
    channel: Optional[str] = None,
    match_browser_version: bool = True,
    args: Optional[List[str]] = None,
    **context_kwargs: Any,
) -> Session:
    """Launch Chromium with ``profile`` fully applied.

    :param proxy: ``"http://host:port"`` or a Playwright proxy dict.
    :param user_data_dir: persistent profile directory (cookies, storage and
        cache survive restarts, like a Dolphin profile). ``None`` = throwaway.
    :param channel: Playwright channel. Default ``"chromium"`` (full Chromium,
        also in headless mode); use ``"chrome"`` for an installed Google Chrome,
        which reports the exact ``Google Chrome`` brand even on the first request
        of a popup. Needs Playwright >= 1.49.
    :param match_browser_version: rewrite a Chrome profile to the real engine
        version, so the claimed version is one the binary really has.
    """
    check_supported(profile)
    profile = dict(profile)
    launch_kwargs: Dict[str, Any] = {
        "headless": headless,
        "args": launch_args(profile) + list(args or []),
        "ignore_default_args": IGNORE_DEFAULT_ARGS,
    }
    # Full Chromium (new headless) never reports a "HeadlessChrome" brand; pass
    # channel="chrome" to use an installed Google Chrome instead.
    launch_kwargs["channel"] = channel or "chromium"
    proxy_cfg = normalize_proxy(proxy)
    if proxy_cfg:
        launch_kwargs["proxy"] = proxy_cfg

    browser = None
    if match_browser_version:
        probe = playwright.chromium.launch(**launch_kwargs)
        try:
            profile = match_engine_version(profile, probe.version)
        finally:
            if user_data_dir:
                probe.close()
        if not user_data_dir:
            browser = probe
    if user_data_dir:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir, **launch_kwargs, **context_options(profile), **context_kwargs
        )
    else:
        browser = browser or playwright.chromium.launch(**launch_kwargs)
        context = browser.new_context(**context_options(profile), **context_kwargs)
    apply_profile(context, profile)
    return Session(context, browser, profile)
