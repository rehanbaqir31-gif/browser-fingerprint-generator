import json
import re
import warnings

import pytest

from fpforge.injector import core


@pytest.fixture(scope="module")
def chrome(generator):
    return generator.generate(os="windows", browser="chrome", country="DE", seed="core")


def test_firefox_and_safari_are_rejected(generator):
    for browser, os_name in (("firefox", "windows"), ("safari", "macos")):
        with pytest.raises(core.UnsupportedProfile):
            core.check_supported(generator.generate(os=os_name, browser=browser, seed="u"))


def test_init_script_embeds_config_and_is_one_expression(chrome):
    src = core.init_script(chrome)
    assert src.endswith(");")
    cfg = json.loads(src[src.rindex("})(") + 3:-2])
    assert cfg["platform"] == chrome["platform"]
    assert cfg["webgl"]["unmaskedRenderer"] == chrome["webgl"]["unmaskedRenderer"]
    assert cfg["languages"] == chrome["languages"]
    assert "codecs" not in cfg["audio"]
    assert src.count("(function (cfg)") == 1


def test_inject_js_has_no_syntax_markers_of_trouble():
    js = core.INJECT_JS.read_text()
    assert js.count("{") == js.count("}") and js.count("(") == js.count(")")
    assert "debugger" not in js and "console." not in js  # must never log from pages


def test_cdp_override_carries_client_hints(chrome):
    p = core.cdp_user_agent_override(chrome)
    meta = p["userAgentMetadata"]
    assert p["userAgent"] == chrome["userAgent"] and p["platform"] == chrome["platform"]
    assert p["acceptLanguage"] == ",".join(chrome["languages"])  # no q-values: Chrome adds them itself
    assert meta["brands"] == chrome["userAgentData"]["brands"]
    assert meta["fullVersionList"] == chrome["userAgentData"]["fullVersionList"]
    assert meta["platformVersion"] == chrome["userAgentData"]["platformVersion"]
    assert meta["mobile"] is False and meta["wow64"] is False


def test_context_options(chrome):
    o = core.context_options(chrome)
    assert o["user_agent"] == chrome["userAgent"] and o["timezone_id"] == chrome["timezone"]
    assert o["locale"] == chrome["language"]
    s = chrome["screen"]
    assert o["screen"] == {"width": s["width"], "height": s["height"]}
    assert 200 <= o["viewport"]["height"] < s["height"] and o["viewport"]["width"] <= s["width"]
    assert o["extra_http_headers"]["Accept-Language"] == chrome["acceptLanguage"]
    assert o["is_mobile"] is False


def test_launch_args_hide_automation_and_protect_webrtc(chrome):
    args = core.launch_args(chrome)
    assert "--disable-blink-features=AutomationControlled" in args
    assert "--force-webrtc-ip-handling-policy=disable_non_proxied_udp" in args
    real = dict(chrome, webrtc={"mode": "real"})
    assert not any("webrtc" in a for a in core.launch_args(real))
    assert "--enable-automation" in core.IGNORE_DEFAULT_ARGS


def test_match_engine_version(chrome, generator):
    out = core.match_engine_version(chrome, "150.0.7000.1")
    assert "Chrome/150.0.0.0" in out["userAgent"] and out["userAgentData"]["uaFullVersion"] == "150.0.7000.1"
    edge = generator.generate(os="windows", browser="edge", seed="e")
    with pytest.warns(UserWarning):
        assert core.match_engine_version(edge, "99.0.0.0") is edge
    major = re.search(r"Edg/(\d+)", edge["userAgent"]).group(1)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        core.match_engine_version(edge, "%s.0.0.0" % major)


def test_normalize_proxy():
    assert core.normalize_proxy(None) is None
    assert core.normalize_proxy("http://h:1") == {"server": "http://h:1"}
    d = {"server": "http://h:1", "username": "u", "password": "p"}
    assert core.normalize_proxy(d) == d and core.normalize_proxy(d) is not d


def test_proxy_credentials_are_split_from_the_url():
    out = core.normalize_proxy("http://us%40er:p%3Ass@proxy.example:8080")
    assert out == {"server": "http://proxy.example:8080", "username": "us@er", "password": "p:ss"}
    assert core.normalize_proxy("socks5://[::1]:1080") == {"server": "socks5://[::1]:1080"}
    assert core.normalize_proxy("http://u@h:1") == {"server": "http://h:1", "username": "u"}
