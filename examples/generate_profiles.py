"""Generate profiles in bulk, one per proxy country.

    python examples/generate_profiles.py            # writes profiles/*.json
"""
import json
from pathlib import Path

from fpforge import FingerprintGenerator

COUNTRIES = ["US", "GB", "DE", "FR", "PK", "JP"]

gen = FingerprintGenerator()
out = Path("profiles")
out.mkdir(exist_ok=True)
for cc in COUNTRIES:
    profile = gen.generate(os="windows", browser="chrome", country=cc)
    (out / ("%s-%s.json" % (cc, profile["fingerprintId"][:8]))).write_text(json.dumps(profile, indent=2))
    print(cc, profile["timezone"], profile["webgl"]["unmaskedRenderer"])
