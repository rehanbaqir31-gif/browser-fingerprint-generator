# Data sources

| File | Origin | Version / date | SHA-256 (first 16) | License |
|---|---|---|---|---|
| `src/fpforge/data/fingerprint-network-definition.zip` | apify/fingerprint-suite, `packages/fingerprint-generator` | master snapshot, 2026-11-08 | 5cc4668d858e0365… | Apache-2.0 |
| `src/fpforge/data/header-network-definition.zip` | apify/fingerprint-suite, `packages/header-generator` | same | 67a17948164967e0… | Apache-2.0 |
| `src/fpforge/data/input-network-definition.zip` | apify/fingerprint-suite, `packages/header-generator` | same | 3b918d231c70202c… | Apache-2.0 |
| `src/fpforge/data/headers-order.json` | apify/fingerprint-suite, `packages/header-generator` | same | 3e89bfcf8f648bd5… | Apache-2.0 |
| `src/fpforge/data/browser-helper-file.json` | apify/fingerprint-suite, `packages/header-generator` | same | 965ee8894d3a4e78… | Apache-2.0 |
| `src/fpforge/data/chrome-stable.json` | Chrome Releases blog; Chrome for Testing | 157.0.8103.38, retrieved 2026-11-08 | n/a | n/a (version number) |
| `COUNTRY_TIMEZONES` in `locale_data.py` | IANA tz database, `zone.tab` | tzdata on build host | n/a | public domain |

Refresh:

```bash
python scripts/update_chrome_version.py   # Chrome stable
python scripts/update_apify_data.py       # Apify network files (validates before writing)
pytest                                     # the tests check the data against itself
```

Hand-written, not from a dataset: `TIMEZONE_WEIGHTS`, `COUNTRY_LANGUAGES` and
`FALLBACK_LOCALES` in `locale_data.py`. Pull requests with better sources are welcome.
