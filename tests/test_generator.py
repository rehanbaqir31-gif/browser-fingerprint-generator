import json
import random

import pytest

from fpforge import FingerprintGenerator, NoMatchingFingerprint
from fpforge.generator import KNOWN_PDF_PLUGINS, SOFTWARE_GPU_MARKERS, classify_user_agent
from fpforge.versions import load_chrome_stable

PLATFORM = {"windows": ("Win32",), "macos": ("MacIntel",), "linux": ("Linux x86_64",)}


@pytest.mark.parametrize(
    "os_name,browser",
    [("windows", "chrome"), ("windows", "edge"), ("windows", "firefox"),
     ("macos", "chrome"), ("macos", "safari"), ("macos", "firefox"),
     ("linux", "chrome"), ("linux", "firefox")],
)
def test_requested_os_and_browser_are_honoured(generator, os_name, browser):
    for i in range(25):
        p = generator.generate(os=os_name, browser=browser, seed="%s-%s-%d" % (os_name, browser, i))
        assert classify_user_agent(p["userAgent"]) == (os_name, browser)
        assert (p["os"], p["browser"]) == (os_name, browser)
        assert p["platform"] in PLATFORM[os_name]


def test_graphics_backend_matches_os(generator):
    """Real-data property: the GPU API string agrees with the operating system."""
    expected = {"windows": "Direct3D11", "macos": "Metal"}
    for os_name, token in expected.items():
        hits = sum(
            token in generator.generate(os=os_name, seed="gpu-%s-%d" % (os_name, i))["webgl"]["unmaskedRenderer"]
            for i in range(200)
        )
        assert hits >= 190, (os_name, hits)


def test_linux_profiles_are_x86_desktops_not_android(generator):
    for i in range(150):
        p = generator.generate(os="linux", seed="lx-%d" % i)
        assert p["platform"] == "Linux x86_64"
        assert not any(g in p["webgl"]["unmaskedRenderer"] for g in ("Adreno", "Mali", "PowerVR"))


def test_seed_is_reproducible_and_distinct(generator):
    a = generator.generate(seed="same")
    b = generator.generate(seed="same")
    c = generator.generate(seed="other")
    assert a == b
    assert a["fingerprintId"] != c["fingerprintId"]
    assert generator.generate_many(5, seed="s") == generator.generate_many(5, seed="s")


def test_fingerprint_ids_are_unique(generator):
    ids = {generator.generate(seed="u-%d" % i)["fingerprintId"] for i in range(300)}
    assert len(ids) == 300


def test_profile_is_json_serialisable_and_complete(generator):
    p = generator.generate(country="DE", seed="shape")
    json.loads(json.dumps(p))
    for key in ("userAgent", "platform", "userAgentData", "screen", "webgl", "canvas", "audio", "fonts",
                "plugins", "battery", "mediaDevices", "languages", "acceptLanguage", "timezone",
                "fingerprintId", "profileUuid", "meta", "hardwareConcurrency", "deviceMemory"):
        assert key in p, key
    assert len(p["fingerprintId"]) == 32
    assert p["webgl"]["vendor"] == "WebKit" and p["webgl"]["renderer"] == "WebKit WebGL"
    assert p["webgl"]["unmaskedRenderer"].startswith("ANGLE")
    assert p["screen"]["width"] > 0 and p["screen"]["height"] > 0
    assert p["fonts"] and p["webdriver"] is False


def test_software_renderers_are_skipped_unless_allowed(generator):
    def renderers(allow):
        rng = random.Random(1)
        return [generator.generate(os="windows", rng=rng, allow_software_gpu=allow, chrome_full=None)
                ["webgl"]["unmaskedRenderer"] for _ in range(400)]

    assert not any(m in r for r in renderers(False) for m in SOFTWARE_GPU_MARKERS)
    assert any(m in r for r in renderers(True) for m in SOFTWARE_GPU_MARKERS)  # they exist in the data


def test_randomised_plugin_records_are_filtered(generator):
    for i in range(150):
        p = generator.generate(os="windows", seed="pl-%d" % i)
        assert {x["name"] for x in p["plugins"]["plugins"]} <= KNOWN_PDF_PLUGINS


def test_chrome_is_retargeted_to_bundled_stable_by_default(generator):
    full = load_chrome_stable()
    major = full.split(".")[0]
    p = generator.generate(os="windows", browser="chrome", seed="rt")
    assert "Chrome/%s.0.0.0" % major in p["userAgent"]
    assert p["userAgentData"]["uaFullVersion"] == full
    assert {"brand": "Google Chrome", "version": major} in p["userAgentData"]["brands"]
    assert p["meta"]["chromeFullVersion"] == full


def test_retarget_can_be_disabled_or_overridden(generator):
    keep = generator.generate(os="windows", seed="rt", chrome_full=None)
    assert "chromeFullVersion" not in keep["meta"]
    custom = generator.generate(os="windows", seed="rt", chrome_full="150.0.7000.1")
    assert "Chrome/150.0.0.0" in custom["userAgent"]
    assert custom["userAgentData"]["uaFullVersion"] == "150.0.7000.1"


def test_non_chrome_browsers_are_never_rewritten(generator):
    for browser in ("edge", "firefox"):
        a = generator.generate(os="windows", browser=browser, seed="nr", chrome_full=None)
        b = generator.generate(os="windows", browser=browser, seed="nr")
        assert a["userAgent"] == b["userAgent"]


def test_country_sets_timezone_and_languages(generator):
    p = generator.generate(country="de", seed="c")
    assert p["country"] == "DE" and p["timezone"] == "Europe/Berlin"
    assert p["language"] == "de-DE" and p["acceptLanguage"].startswith("de-DE,de;q=0.9")


def test_without_country_a_fallback_locale_is_used(generator):
    p = generator.generate(seed="nc")
    assert p["country"] is None and p["timezone"] and p["languages"]


def test_invalid_arguments(generator):
    with pytest.raises(ValueError):
        generator.generate(os="beos")
    with pytest.raises(ValueError):
        generator.generate(browser="netscape")
    with pytest.raises(ValueError):
        generator.generate(country="XX")
    with pytest.raises(NoMatchingFingerprint):
        generator.generate(os="linux", browser="safari")


def test_available_reports_dataset_contents(generator):
    avail = generator.available()
    assert avail[("windows", "chrome")] > 10
    assert ("linux", "safari") not in avail
