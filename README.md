# fpforge

Realistic, internally consistent browser fingerprint profiles, and a Playwright
integration that applies them to Chromium.

Every device attribute (user agent, client hints, GPU, screen, fonts, cores,
memory, plugins, codecs, battery, media devices) is sampled **jointly** from a
trained model of real browser traffic, so the combinations are ones real
browsers produce. Timezone and language are then chosen to match a proxy's
country.

> **Responsible use.** fpforge is for privacy research, QA testing of your own
> sites, and automation that you are allowed to run. Do not use it to evade
> bans, fraud, or account abuse, and follow each site's terms and your local
> law.

## Features

- Real-data generator: `FingerprintGenerator().generate(os="macos", country="DE")`
- Consistent profiles for Chrome, Edge, Firefox and Safari (desktop)
- Chrome version rewrite to the bundled stable (or the engine's real version)
- Playwright injector (sync and async): overrides `navigator`, `screen`, WebGL,
  canvas, audio, battery, media devices, client hints and `Accept-Language`,
  with native-looking `toString`
- Matching HTTP headers for plain HTTP clients
- CLI: `fpforge generate | headers | launch | info`
- Persistent profiles (`user_data_dir`) and proxy support with credentials

## Install

```bash
pip install fpforge                 # generator + CLI
pip install "fpforge[playwright]"   # + Playwright integration
playwright install chromium
```

From a checkout:

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from playwright.sync_api import sync_playwright
from fpforge import FingerprintGenerator
from fpforge.injector.sync_api import launch_context

profile = FingerprintGenerator().generate(os="windows", browser="chrome", country="DE")

with sync_playwright() as p, launch_context(p, profile, proxy="http://user:pass@host:8080") as s:
    page = s.new_page()
    page.goto("https://example.com")
```

CLI:

```bash
fpforge generate --os macos --country US -n 10 -o profiles.json
fpforge headers --country DE --http-version 2
fpforge launch profiles.json --url https://example.com --user-data-dir ./profiles/a
fpforge info
```

## How the data works

| Part | Source | Real data? |
|---|---|---|
| Device profile (UA, GPU, screen, fonts, cores, memory, plugins, codecs, client hints, ...) | Apify `fingerprint-network-definition.zip` (trained Bayesian network) | Yes, trained on real browser traffic |
| HTTP header sets | Apify `header-network-definition.zip`, `input-network-definition.zip` | Yes |
| Header order, browser helper list | Apify `headers-order.json`, `browser-helper-file.json` | Yes |
| Timezone per country | IANA tz database (`zone.tab`) | Yes |
| Chrome stable version | Chrome for Testing / Chrome Releases | Yes, refreshed by a script |
| Population weights for multi-zone countries | Written by hand | **No, approximate** |
| Languages per country | Written by hand | **No, curated** |
| Canvas/audio noise seeds, WebRTC mode | Generated | Not a dataset |

See [DATA_SOURCES.md](DATA_SOURCES.md) for versions, hashes and how to update.

## Known limitations

These are stated plainly so you can decide whether they matter for your use.

- **Dedicated workers are not reliably covered.** A worker that starts while
  the page loads can run before the override is applied (about 15% of runs in
  our measurements). Workers created after load are often correct but not
  guaranteed. The main frame, iframes, popups and HTTP requests are exact.
  Tests for workers are marked `xfail` with this reason.
- **A popup's first request** may carry Playwright's default client hints when
  the Chromium channel is used. JavaScript values and later requests are exact.
- **Edge profiles cannot be rewritten** to the engine's version (their Edge
  build number is unknown). A warning is raised when they differ.
- **Firefox and Safari profiles** cannot be applied by the Chromium injector.
  Generating them and using their headers works.
- **Timezone and language** are not in the dataset; they come from the tables
  in `locale_data.py`. The proxy's exit country must match `country=`, or
  sites will see a mismatch.
- **Canvas and audio noise** make hashes differ from the real device's; a
  site that compares against known real hashes will notice.
- The dataset is a snapshot. Refresh it with `scripts/update_apify_data.py`.

## Development

```bash
pip install -e ".[dev]"
playwright install chromium
pytest
mypy src
```

The end-to-end tests launch a real Chromium against a local server; they skip
when Chromium is not installed.

## Project layout

```
src/fpforge/
  generator.py      FingerprintGenerator (dataset sampling, filters)
  network.py        Bayesian network sampler (port of Apify's TypeScript)
  versions.py       Chrome version rewrite and GREASE brand rules
  headers.py        HTTP header generator
  locale_data.py    country -> timezone / language (see provenance in file)
  cli.py            command line
  injector/         Playwright integration (core, sync_api, async_api, inject.js)
  data/             bundled datasets (Apache-2.0, see NOTICE)
tests/              unit tests and real-browser end-to-end tests
scripts/            refresh Chrome version and Apify data
examples/           runnable examples
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

Apache-2.0. Bundled third-party data is Apache-2.0 as well; see [NOTICE](NOTICE).
