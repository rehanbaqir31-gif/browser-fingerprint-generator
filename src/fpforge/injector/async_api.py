"""Asynchronous Playwright integration (mirror of :mod:`fpforge.injector.sync_api`).

    async with async_playwright() as p:
        session = await launch_context(p, profile)
        page = await session.new_page()
        ...
        await session.close()
"""
from __future__ import annotations

import asyncio
import warnings
from typing import Any, Dict, List, Mapping, Optional

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
    def __init__(self, context: Any, browser: Any, profile: Dict[str, Any]):
        self.context = context
        self.browser = browser
        self.profile = profile

    async def new_page(self) -> Any:
        return await self.context.new_page()

    async def close(self) -> None:
        await self.context.close()
        if self.browser is not None:
            await self.browser.close()

    async def __aenter__(self) -> "Session":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()


async def _patch_workers(cdp: Any, messages: List[str]) -> None:
    """Run the override script inside every dedicated worker before its own code starts."""

    async def patch(event: Any) -> None:
        try:
            for message in messages:
                await cdp.send("Target.sendMessageToTarget", {"sessionId": event["sessionId"], "message": message})
        except Exception as exc:  # worker already gone
            warnings.warn("could not patch worker: %s" % exc)

    def on_attached(event: Any) -> None:
        if event["targetInfo"]["type"] in WORKER_TARGET_TYPES:
            asyncio.ensure_future(patch(event))

    cdp.on("Target.attachedToTarget", on_attached)
    await cdp.send("Target.setAutoAttach", AUTO_ATTACH_WORKERS)


async def apply_profile(context: Any, profile: Mapping[str, Any]) -> None:
    check_supported(profile)
    ua_params = cdp_user_agent_override(profile)
    worker_messages = worker_setup_messages(profile)
    await context.add_init_script(init_script(profile))

    sessions: Dict[int, Any] = {}  # one CDP session per page, reused on re-apply

    async def hook(page: Any) -> None:
        try:
            cdp = sessions.get(id(page))
            if cdp is None:
                cdp = sessions[id(page)] = await context.new_cdp_session(page)
                page.once("close", lambda *_: sessions.pop(id(page), None))
                await _patch_workers(cdp, worker_messages)
            await cdp.send("Emulation.setUserAgentOverride", ua_params)
        except Exception as exc:
            warnings.warn("could not apply user-agent override: %s" % exc)

    for page in list(context.pages):
        await hook(page)

    # Apply once the page is ready, before new_page() returns, so it precedes any
    # navigation; the event hook covers pages opened by scripts (popups).
    # Applying twice is harmless: the overrides are idempotent.
    original_new_page = context.new_page

    async def new_page(*args: Any, **kwargs: Any) -> Any:
        page = await original_new_page(*args, **kwargs)
        await hook(page)
        return page

    context.new_page = new_page
    context.on("page", lambda page: asyncio.ensure_future(hook(page)))


async def launch_context(
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
        probe = await playwright.chromium.launch(**launch_kwargs)
        try:
            profile = match_engine_version(profile, probe.version)
        finally:
            if user_data_dir:
                await probe.close()
        if not user_data_dir:
            browser = probe
    if user_data_dir:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir, **launch_kwargs, **context_options(profile), **context_kwargs
        )
    else:
        browser = browser or await playwright.chromium.launch(**launch_kwargs)
        context = await browser.new_context(**context_options(profile), **context_kwargs)
    await apply_profile(context, profile)
    return Session(context, browser, profile)
