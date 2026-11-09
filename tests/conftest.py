import pytest

from fpforge import FingerprintGenerator


@pytest.fixture(scope="session")
def generator():
    return FingerprintGenerator()
