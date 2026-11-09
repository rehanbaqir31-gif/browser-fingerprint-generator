import random
import zoneinfo

import pytest

from fpforge import locale_data as L


def test_every_country_has_timezones_and_a_valid_default():
    assert len(L.COUNTRY_TIMEZONES) >= 240
    rng = random.Random(0)
    for cc in L.COUNTRY_TIMEZONES:
        assert L.COUNTRY_TIMEZONES[cc]
        assert L.pick_timezone(cc, rng) in L.COUNTRY_TIMEZONES[cc]


def test_timezone_names_exist_in_tzdata():
    available = zoneinfo.available_timezones()
    if not available:
        pytest.skip("no tz database on this system")
    missing = [z for zs in L.COUNTRY_TIMEZONES.values() for z in zs if z not in available]
    assert not missing[:5], missing


def test_weight_tables_reference_real_zones():
    for cc, weights in L.TIMEZONE_WEIGHTS.items():
        assert set(weights) <= set(L.COUNTRY_TIMEZONES[cc]), cc


def test_known_fixes_and_defaults():
    rng = random.Random(0)
    assert {L.pick_timezone("UA", rng) for _ in range(20)} == {"Europe/Kyiv"}
    assert L.pick_timezone("PK", rng) == "Asia/Karachi"
    assert L.pick_timezone("DE", rng) == "Europe/Berlin"
    assert L.pick_timezone("JP", rng) == "Asia/Tokyo"


def test_multizone_distribution_is_dominated_by_populous_zones():
    rng = random.Random(1)
    picks = [L.pick_timezone("US", rng) for _ in range(3000)]
    assert picks.count("America/New_York") > picks.count("America/Los_Angeles") > picks.count("Pacific/Honolulu")
    assert "America/Kentucky/Monticello" not in picks


def test_accept_language_format():
    assert L.build_accept_language(["en-US", "en"]) == "en-US,en;q=0.9"
    assert L.build_accept_language(["de-DE", "de", "en-US", "en"]) == "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
    assert L.build_accept_language(["fr"]) == "fr"


def test_locale_for_unknown_country_raises():
    with pytest.raises(ValueError):
        L.locale_for("ZZ", random.Random(0))


def test_locale_for_is_case_insensitive_and_consistent():
    langs, tz, header = L.locale_for("fr", random.Random(0))
    assert langs[0] == "fr-FR" and tz == "Europe/Paris" and header.startswith("fr-FR,fr;q=0.9")


def test_fallback_locale():
    langs, tz, header = L.fallback_locale(random.Random(0))
    assert langs and tz and header.split(",")[0] == langs[0]
