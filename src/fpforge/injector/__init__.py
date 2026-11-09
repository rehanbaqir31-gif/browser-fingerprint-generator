"""Apply a fpforge profile to a Playwright Chromium browser.

Import the integration you need; Playwright is imported only by your code:

* :mod:`fpforge.injector.sync_api`  - ``launch_context`` / ``apply_profile``
* :mod:`fpforge.injector.async_api` - the same, with ``await``
* :mod:`fpforge.injector.core`      - pure helpers (options, init script, CDP params)
"""
from .core import (
    UnsupportedProfile,
    cdp_user_agent_override,
    context_options,
    init_script,
    launch_args,
)

__all__ = [
    "UnsupportedProfile",
    "cdp_user_agent_override",
    "context_options",
    "init_script",
    "launch_args",
]
