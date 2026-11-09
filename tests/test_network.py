import random

from fpforge.generator import classify_user_agent


def test_unrestricted_sampling_follows_the_trained_distribution(generator):
    net = generator.network
    root = net.by_name["userAgent"]["conditionalProbabilities"]
    expected = sum(p for ua, p in root.items() if classify_user_agent(ua)[0] == "windows")
    rng = random.Random(0)
    n = 4000
    hits = sum(classify_user_agent(net.generate_sample(rng)["userAgent"])[0] == "windows" for _ in range(n))
    assert abs(hits / n - expected) < 0.03


def test_restricted_sampling_only_returns_allowed_values(generator):
    net = generator.network
    allowed = [u for u in net.by_name["userAgent"]["possibleValues"] if classify_user_agent(u) == ("macos", "safari")]
    rng = random.Random(1)
    for _ in range(50):
        s = net.generate_consistent_sample(rng, {"userAgent": allowed})
        assert s["userAgent"] in allowed


def test_impossible_restriction_returns_none(generator):
    assert generator.network.generate_consistent_sample(random.Random(2), {"userAgent": ["not a real ua"]}) is None


def test_sample_contains_every_node(generator):
    s = generator.network.generate_sample(random.Random(3))
    assert set(s) == {n["name"] for n in generator.network.nodes}
