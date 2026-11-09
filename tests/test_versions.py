import copy

from fpforge.generator import decode
from fpforge.versions import (
    BRAND_ORDERS, chrome_brands, grease_brand, load_chrome_stable, major_of, retarget_chrome,
)


def test_grease_rule_matches_known_real_chrome_values():
    # values seen in real Chrome release notes / sec-ch-ua headers
    assert grease_brand(147) == ("Not.A/Brand", "8")
    assert grease_brand(144) == ("Not(A:Brand", "8")
    assert grease_brand(146) == ("Not-A.Brand", "24")
    assert grease_brand(153) == ("Not_A Brand", "8")


def test_grease_rule_against_the_bundled_dataset(generator):
    """The rewrite logic must reproduce what real Chrome browsers in the dataset report."""
    total = ok = 0
    for raw in generator.network.by_name["userAgentData"]["possibleValues"]:
        d = decode(raw)
        if not isinstance(d, dict):
            continue
        brands = d.get("brands") or []
        names = [b["brand"] for b in brands]
        if len(names) != 3 or "Google Chrome" not in names or "Microsoft Edge" in names:
            continue
        major = int(next(b for b in brands if b["brand"] == "Google Chrome")["version"])
        full = next(b for b in d["fullVersionList"] if b["brand"] == "Google Chrome")["version"]
        total += 1
        ok += chrome_brands(major, full) == (d["brands"], d["fullVersionList"])
    assert total > 500
    assert ok / total >= 0.97, "%d/%d" % (ok, total)  # the rest are Chromium forks with other naming


def test_brand_orders_are_permutations():
    assert all(sorted(v) == ["B", "C", "G"] for v in BRAND_ORDERS.values())
    assert set(BRAND_ORDERS) == set(range(6))


def test_chrome_brands_shape():
    brands, full = chrome_brands(157, "157.0.8103.38")
    assert len(brands) == len(full) == 3
    assert {"brand": "Google Chrome", "version": "157"} in brands
    assert {"brand": "Chromium", "version": "157.0.8103.38"} in full


def test_retarget_does_not_mutate_input_and_ignores_other_browsers(generator):
    chrome = generator.generate(os="windows", browser="chrome", seed="v", chrome_full=None)
    snapshot = copy.deepcopy(chrome)
    out = retarget_chrome(chrome, "150.0.7000.1")
    assert chrome == snapshot and out is not chrome
    edge = generator.generate(os="windows", browser="edge", seed="v", chrome_full=None)
    assert retarget_chrome(edge, "150.0.7000.1")["userAgent"] == edge["userAgent"]


def test_bundled_chrome_version_is_wellformed():
    v = load_chrome_stable()
    parts = v.split(".")
    assert len(parts) == 4 and all(p.isdigit() for p in parts)
    assert major_of(v) >= 140
