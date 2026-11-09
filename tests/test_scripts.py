import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_chrome_version.py"


def _load():
    spec = importlib.util.spec_from_file_location("update_chrome_version", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_chrome_for_testing_payload():
    mod = _load()
    payload = {"timestamp": "2026-11-08T00:00:00.000Z",
               "channels": {"Stable": {"channel": "Stable", "version": "157.0.8103.38", "revision": "1"},
                            "Beta": {"channel": "Beta", "version": "158.0.1.1", "revision": "2"}}}
    assert mod.parse(payload) == "157.0.8103.38"


def test_parse_rejects_garbage():
    mod = _load()
    for bad in ({}, {"channels": {}}, {"channels": {"Stable": {"version": "abc"}}}):
        with pytest.raises(ValueError):
            mod.parse(bad)


def test_write_roundtrip(tmp_path):
    mod = _load()
    target = tmp_path / "chrome-stable.json"
    mod.write(target, "157.0.8103.38", "https://example.invalid/x.json", today="2026-11-08")
    data = json.loads(target.read_text())
    assert data["version"] == "157.0.8103.38" and data["retrieved"] == "2026-11-08"
