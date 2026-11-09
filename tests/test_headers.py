import pytest

from fpforge import HeaderGenerator


@pytest.fixture(scope="module")
def hg():
    return HeaderGenerator()


def _profile(generator, os_name, browser, seed="h"):
    return generator.generate(os=os_name, browser=browser, seed=seed, country="DE")


def test_chrome_headers_agree_with_the_profile(generator, hg):
    p = _profile(generator, "windows", "chrome")
    h = hg.generate(p, seed=1)
    assert h["user-agent"] == p["userAgent"]
    assert h["accept-language"] == p["acceptLanguage"]
    brands = ", ".join('"%s";v="%s"' % (b["brand"], b["version"]) for b in p["userAgentData"]["brands"])
    assert h["sec-ch-ua"] == brands
    assert h["sec-ch-ua-platform"] == '"Windows"' and h["sec-ch-ua-mobile"] == "?0"
    assert h["sec-fetch-mode"] == "navigate" and h["sec-fetch-dest"] == "document"
    assert h["sec-fetch-site"] == "none" and h["sec-fetch-user"] == "?1"
    assert "text/html" in h["accept"] and "gzip" in h["accept-encoding"]


def test_firefox_has_no_client_hints(generator, hg):
    h = hg.generate(_profile(generator, "windows", "firefox"), seed=1)
    assert not any(k.startswith("sec-ch-ua") for k in h)
    assert h["user-agent"].count("Firefox/") == 1


def test_safari_headers(generator, hg):
    p = _profile(generator, "macos", "safari")
    h = hg.generate(p, seed=1)
    assert h["user-agent"] == p["userAgent"] and "sec-ch-ua" not in h


def test_http1_uses_pascal_case_names(generator, hg):
    p = _profile(generator, "windows", "chrome")
    h1 = hg.generate(p, http_version="1", seed=1)
    assert "User-Agent" in h1 and "Accept-Language" in h1 and "user-agent" not in h1
    assert "sec-ch-ua" in h1  # client hints are always lower-case
    assert "Sec-Fetch-Mode" in h1


def test_same_seed_same_headers_and_order(generator, hg):
    p = _profile(generator, "windows", "chrome")
    a, b = hg.generate(p, seed=7), hg.generate(p, seed=7)
    assert list(a.items()) == list(b.items())


def test_header_order_follows_chrome_order(generator, hg):
    h = hg.generate(_profile(generator, "windows", "chrome"), seed=3)
    keys = list(h)
    assert keys.index("sec-ch-ua") < keys.index("user-agent") < keys.index("accept")


def test_extra_headers_and_cross_site(generator, hg):
    h = hg.generate(_profile(generator, "windows", "chrome"), seed=1,
                    sec_fetch_site="cross-site", extra={"referer": "https://example.com/"})
    assert h["sec-fetch-site"] == "cross-site" and h["referer"] == "https://example.com/"


def test_invalid_http_version(generator, hg):
    with pytest.raises(ValueError):
        hg.generate(_profile(generator, "windows", "chrome"), http_version="3")
