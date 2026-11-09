# Changelog

## Unreleased
- Profiles are only accepted when they carry a GPU vendor and renderer, so the real WebGL renderer can never leak through a profile without one.
- Engine version is probed once per process and channel, not on every launch.
- `.gitattributes` marks the bundled zip files as binary.
- Worker-patching code and tests cover the known race; see README "Known limitations".

## 0.1.0 - 2026-11-09
- Real-data generator backed by Apify's trained network (Windows, macOS, Linux; Chrome, Edge, Firefox, Safari).
- Chrome version rewrite with GREASE brand rules, validated against the dataset.
- Playwright sync and async injector, persistent profiles, proxy credentials.
- HTTP header generator, CLI (`generate`, `headers`, `launch`, `info`).
- Known limitation: dedicated worker coverage is best-effort (see README).
