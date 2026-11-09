"""Shared test helpers."""


def last_request(seen):
    """The most recent top-level document request recorded by the test server."""
    docs = [h for h in seen if h.get("sec-fetch-dest") == "document"]
    return (docs or seen)[-1]
