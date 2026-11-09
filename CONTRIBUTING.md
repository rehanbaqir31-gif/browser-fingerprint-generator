# Contributing

Thanks for helping. Please keep changes focused and tested.

1. Fork and create a branch.
2. `pip install -e ".[dev]" && playwright install chromium`
3. `pytest` and `mypy src` must pass.
4. Data changes: say where the data came from (URL, date, license) in the PR and
   update `DATA_SOURCES.md`. Do not add data you cannot redistribute.
5. Do not add telemetry, network calls at import time, or anything that sends
   user data anywhere.

Code style: standard library first; Python 3.9+ syntax only.
