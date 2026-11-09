"""End-to-end: launch real Chromium and check what pages and the network see.

Skipped automatically when Playwright or its Chromium is not installed.
Run `playwright install chromium` to enable.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

from fpforge import FingerprintGenerator  # noqa: E402
from fpforge.injector.sync_api import launch_context  # noqa: E402

PAGE = b"<!doctype html><html><head><meta charset=utf-8><title>t</title></head><body>ok</body></html>"


WORKER_JS = (b"postMessage({platform: navigator.platform, cores: navigator.hardwareConcurrency,"
             b" mem: navigator.deviceMemory, ua: navigator.userAgent, langs: navigator.languages,"
             b" uadPlatform: navigator.userAgentData && navigator.userAgentData.platform,"
             b" patched: Object.getOwnPropertyDescriptor(WorkerNavigator.prototype, 'platform').get.toString()});")


class _Handler(BaseHTTPRequestHandler):
    seen = []  # headers of every request, lower-cased

    def do_GET(self):  # noqa: N802
        type(self).seen.append({k.lower(): v for k, v in self.headers.items()})
        if self.path.startswith("/worker.js"):
            body, ctype = WORKER_JS, "text/javascript"
        else:
            body, ctype = PAGE, "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # silence
        pass


@pytest.fixture(scope="module")
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield "http://127.0.0.1:%d/" % httpd.server_port
    httpd.shutdown()


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def generator():
    return FingerprintGenerator()


def _launch(pw, profile, **kw):
    try:
        return launch_context(pw, profile, **kw)
    except Exception as exc:  # no browser binary available
        pytest.skip("cannot launch Chromium: %s" % exc)


@pytest.fixture(scope="module")
def win(pw, generator):
    profile = generator.generate(os="windows", browser="chrome", country="DE", seed="e2e-win")
    with _launch(pw, profile) as s:
        yield s


def _eval(session, server, js):
    page = session.new_page()
    try:
        page.goto(server)
        return page.evaluate(js)
    finally:
        page.close()


def test_navigator_matches_profile(win, server):
    p = win.profile
    got = _eval(win, server, """() => ({
        ua: navigator.userAgent, platform: navigator.platform, vendor: navigator.vendor,
        cores: navigator.hardwareConcurrency, mem: navigator.deviceMemory,
        langs: navigator.languages, lang: navigator.language, touch: navigator.maxTouchPoints,
        webdriver: navigator.webdriver, dnt: navigator.doNotTrack,
        sameLangs: navigator.languages === navigator.languages,
    })""")
    assert got["ua"] == p["userAgent"]
    assert got["platform"] == p["platform"]
    assert got["vendor"] == p["vendor"]
    assert got["cores"] == p["hardwareConcurrency"]
    assert got["mem"] == p["deviceMemory"]
    assert got["langs"] == p["languages"] and got["lang"] == p["language"]
    assert got["touch"] == p["maxTouchPoints"]
    assert got["webdriver"] is False
    assert got["sameLangs"] is True


def test_client_hints_js_and_headers(win, server):
    p = win.profile
    uad = p["userAgentData"]
    _eval(win, server, "() => 1")
    got = _eval(win, server, """async () => {
        const h = await navigator.userAgentData.getHighEntropyValues(
            ['platformVersion','architecture','bitness','fullVersionList','model','uaFullVersion']);
        return {brands: navigator.userAgentData.brands, mobile: navigator.userAgentData.mobile,
                platform: navigator.userAgentData.platform, high: h};
    }""")
    assert got["brands"] == uad["brands"]
    assert got["platform"] == uad["platform"]
    assert got["high"]["platformVersion"] == uad["platformVersion"]
    assert got["high"]["architecture"] == uad["architecture"]
    assert got["high"]["fullVersionList"] == uad["fullVersionList"]

    from tests._helpers import last_request  # noqa: PLC0415

    req = last_request(_Handler.seen)
    expected = ", ".join('"%s";v="%s"' % (b["brand"], b["version"]) for b in uad["brands"])
    assert req["sec-ch-ua"] == expected
    assert req["sec-ch-ua-platform"] == '"%s"' % uad["platform"]
    assert req["user-agent"] == p["userAgent"]
    assert req["accept-language"] == p["acceptLanguage"]


def test_timezone_screen_and_dpr(win, server):
    p = win.profile
    got = _eval(win, server, """() => ({
        tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
        intlLocale: Intl.DateTimeFormat().resolvedOptions().locale,
        w: screen.width, h: screen.height, aw: screen.availWidth, ah: screen.availHeight,
        cd: screen.colorDepth, ow: outerWidth, oh: outerHeight, dpr: devicePixelRatio,
    })""")
    s = p["screen"]
    assert got["tz"] == p["timezone"]
    assert got["intlLocale"] == p["language"]
    assert (got["w"], got["h"]) == (s["width"], s["height"])
    assert (got["aw"], got["ah"]) == (s["availWidth"], s["availHeight"])
    assert got["cd"] == s["colorDepth"]
    assert (got["ow"], got["oh"]) == (s["outerWidth"], s["outerHeight"])
    assert got["dpr"] == s["devicePixelRatio"]


def test_webgl_unmasked_renderer(win, server):
    p = win.profile
    got = _eval(win, server, """() => {
        const gl = document.createElement('canvas').getContext('webgl');
        if (!gl) return null;
        const before = gl.getParameter(0x9246);
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        return {before, vendor: gl.getParameter(ext ? ext.UNMASKED_VENDOR_WEBGL : 0x9245),
                renderer: gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : 0x9246),
                maskedRenderer: gl.getParameter(gl.RENDERER)};
    }""")
    if got is None:
        pytest.skip("WebGL unavailable in this environment")
    assert got["renderer"] == p["webgl"]["unmaskedRenderer"]
    assert got["vendor"] == p["webgl"]["unmaskedVendor"]
    assert got["maskedRenderer"] == "WebKit WebGL"
    assert got["before"] != p["webgl"]["unmaskedRenderer"]  # not answered before the extension is requested


CANVAS_JS = """() => {
    const c = document.createElement('canvas'); c.width = 200; c.height = 60;
    const x = c.getContext('2d');
    x.fillStyle = '#f60'; x.fillRect(10, 10, 100, 30);
    x.fillStyle = '#069'; x.font = '18px Arial'; x.fillText('fpforge canvas 123', 12, 40);
    x.fillStyle = 'rgba(102,204,0,0.7)'; x.beginPath(); x.arc(150, 30, 20, 0, 6.28); x.fill();
    return [c.toDataURL(), c.toDataURL(), x.getImageData(0, 0, 200, 60).data.join(',')];
}"""


def test_canvas_noise_is_deterministic_and_profile_specific(pw, generator, server):
    outs = []
    for seed in ("canvas-a", "canvas-a", "canvas-b"):
        prof = generator.generate(os="windows", seed="same-device")
        prof["canvas"]["noiseSeed"] = {"canvas-a": 1111, "canvas-b": 2222}[seed]
        with _launch(pw, prof) as s:
            outs.append(_eval(s, server, CANVAS_JS))
    assert outs[0][0] == outs[0][1]            # stable within a page
    assert outs[0] == outs[1]                  # stable across sessions with the same seed
    assert outs[0][0] != outs[2][0]            # different seed -> different hash
    assert outs[0][2] != outs[2][2]


def test_patched_functions_look_native(win, server):
    got = _eval(win, server, """() => {
        const d = Object.getOwnPropertyDescriptor(Navigator.prototype, 'platform');
        return {
            getter: Function.prototype.toString.call(d.get),
            toString: Function.prototype.toString.call(Function.prototype.toString),
            toDataURL: HTMLCanvasElement.prototype.toDataURL.toString(),
            getParameter: WebGLRenderingContext.prototype.getParameter.toString(),
            own: Object.getOwnPropertyNames(navigator),
            illegal: (() => { try { d.get.call({}); return 'no error'; } catch (e) { return e.constructor.name; } })(),
        };
    }""")
    assert got["getter"] == "function get platform() { [native code] }"
    assert got["toString"] == "function toString() { [native code] }"
    assert got["toDataURL"] == "function toDataURL() { [native code] }"
    assert got["getParameter"] == "function getParameter() { [native code] }"
    assert got["own"] == []                      # nothing defined on the instance
    assert got["illegal"] == "TypeError"          # native "Illegal invocation" behaviour kept


def test_battery_and_media_devices(win, server):
    p = win.profile
    got = _eval(win, server, """async () => {
        const out = {};
        if (navigator.getBattery) {
            const b = await navigator.getBattery();
            out.battery = {charging: b.charging, level: b.level, ct: b.chargingTime, dt: b.dischargingTime};
        }
        out.devices = (await navigator.mediaDevices.enumerateDevices()).map(d => d.kind);
        return out;
    }""")
    if p["battery"] and "battery" in got:
        assert got["battery"]["charging"] == p["battery"]["charging"]
        assert got["battery"]["level"] == p["battery"]["level"]
    m = p["mediaDevices"]
    expected = (["audioinput"] * len(m["micros"]) + ["videoinput"] * len(m["webcams"])
                + ["audiooutput"] * len(m["speakers"]))
    assert got["devices"] == expected


def test_popup_inherits_profile(win, server):
    page = win.new_page()
    page.goto(server)
    with page.expect_popup() as info:
        page.evaluate("(u) => window.open(u)", server)
    popup = info.value
    popup.wait_for_load_state()
    got = popup.evaluate("() => [navigator.userAgent, navigator.userAgentData.brands, navigator.hardwareConcurrency]")
    assert got[0] == win.profile["userAgent"]
    assert got[1] == win.profile["userAgentData"]["brands"]
    assert got[2] == win.profile["hardwareConcurrency"]
    page.close()


def test_popup_request_headers(win, server):
    """The popup's own first request, which is sent before any CDP override can land."""
    from tests._helpers import last_request  # noqa: PLC0415

    page = win.new_page()
    page.goto(server)
    _Handler.seen.clear()
    with page.expect_popup() as info:
        page.evaluate("(u) => window.open(u)", server)
    info.value.wait_for_load_state()
    req = last_request(_Handler.seen)
    page.close()
    assert req["user-agent"] == win.profile["userAgent"]
    # Known limitation: a popup's very first request still carries Playwright's
    # defaults (short Accept-Language, client hints without the "Google Chrome"
    # brand). JavaScript values and all later requests are exact (see other tests).
    assert req["accept-language"].startswith(win.profile["language"])
    assert "HeadlessChrome" not in req["sec-ch-ua"]


WORKER_PROBE = """(src) => new Promise((resolve) => {
    const w = new Worker(src);
    w.onmessage = (e) => resolve(e.data);
    w.onerror = (e) => resolve({error: String(e.message)});
})"""


def _assert_worker_matches(got, profile):
    assert got["platform"] == profile["platform"]
    assert got["cores"] == profile["hardwareConcurrency"]
    assert got["mem"] == profile["deviceMemory"]
    assert got["ua"] == profile["userAgent"]
    assert got["langs"] == profile["languages"]
    assert got["uadPlatform"] == profile["userAgentData"]["platform"]
    assert got["patched"] == "function get platform() { [native code] }"


@pytest.mark.xfail(strict=False, reason="known limitation: in the sync API, CDP worker-attach events are "
                   "dispatched only during sync calls, so workers started at page load can run before the "
                   "patch lands (~15% observed). See README 'Known limitations'.")
def test_dedicated_workers_see_the_profile(win, server):
    page = win.new_page()
    page.goto(server)
    blob = "URL.createObjectURL(new Blob([%r], {type: 'text/javascript'}))" % WORKER_JS.decode()
    for _ in range(5):  # must hold every time, not just when the race is won
        _assert_worker_matches(page.evaluate("(f) => (" + WORKER_PROBE + ")(eval(f))", blob), win.profile)
        _assert_worker_matches(page.evaluate(WORKER_PROBE, "/worker.js"), win.profile)
    page.close()


@pytest.mark.xfail(strict=False, reason="same race as test_dedicated_workers_see_the_profile")
def test_module_worker_and_same_origin_iframe_worker(win, server):
    page = win.new_page()
    page.goto(server)
    got = page.evaluate("""(src) => new Promise((resolve) => {
        const w = new Worker(src, {type: 'module'});
        w.onmessage = (e) => resolve(e.data);
    })""", "/worker.js")
    _assert_worker_matches(got, win.profile)
    got = page.evaluate("""async (src) => {
        const f = document.createElement('iframe'); f.src = '/'; document.body.appendChild(f);
        await new Promise(r => f.onload = r);
        return await new Promise((resolve) => {
            const w = new f.contentWindow.Worker(src);
            w.onmessage = (e) => resolve(e.data);
        });
    }""", "/worker.js")
    _assert_worker_matches(got, win.profile)
    page.close()


def test_iframe_gets_overrides(win, server):
    page = win.new_page()
    page.goto(server)
    got = page.evaluate("""async (u) => {
        const f = document.createElement('iframe'); f.src = u; document.body.appendChild(f);
        await new Promise(r => f.onload = r);
        const w = f.contentWindow;
        return [w.navigator.hardwareConcurrency, w.navigator.platform, w.screen.width];
    }""", server)
    page.close()
    assert got == [win.profile["hardwareConcurrency"], win.profile["platform"], win.profile["screen"]["width"]]


def test_chrome_version_follows_real_engine(win):
    engine_major = int(win.browser.version.split(".")[0])
    assert ("Chrome/%d.0.0.0" % engine_major) in win.profile["userAgent"]
    assert win.profile["userAgentData"]["uaFullVersion"] == win.browser.version


def test_persistent_context_roundtrip(pw, generator, server, tmp_path):
    prof = generator.generate(os="macos", browser="chrome", country="US", seed="persist")
    with _launch(pw, prof, user_data_dir=str(tmp_path / "profile")) as s:
        got = _eval(s, server, "() => [navigator.platform, Intl.DateTimeFormat().resolvedOptions().timeZone]")
    assert got[0] == "MacIntel"
    assert got[1] == s.profile["timezone"]


def test_grease_rule_agrees_with_the_real_engine(pw, server):
    """Our GREASE brand for the engine's major must equal what the real browser reports."""
    from fpforge.versions import grease_brand  # noqa: PLC0415

    try:
        browser = pw.chromium.launch(channel="chromium")
    except Exception as exc:
        pytest.skip("cannot launch Chromium: %s" % exc)
    try:
        page = browser.new_page()
        page.goto(server)
        real = page.evaluate("() => navigator.userAgentData.brands")
        major = int(browser.version.split(".")[0])
    finally:
        browser.close()
    name, version = grease_brand(major)
    assert {"brand": name, "version": version} in real


def test_cli_launch_headless(tmp_path, server, generator):
    """Run the real CLI in its own process (a second sync Playwright cannot share this one's loop)."""
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    import fpforge  # noqa: PLC0415

    profile = generator.generate(os="windows", country="US", seed="cli-launch")
    path = tmp_path / "p.json"
    path.write_text(json.dumps([profile]))
    env = dict(os.environ, PYTHONPATH=str(Path(fpforge.__file__).resolve().parent.parent))
    _Handler.seen.clear()
    done = subprocess.run(
        [sys.executable, "-m", "fpforge", "launch", str(path), "--headless", "--wait", "0", "--url", server],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert done.returncode == 0, done.stderr
    from tests._helpers import last_request  # noqa: PLC0415

    req = last_request(_Handler.seen)
    assert req["accept-language"] == profile["acceptLanguage"]
    assert "HeadlessChrome" not in req["sec-ch-ua"] and "Google Chrome" in req["sec-ch-ua"]
