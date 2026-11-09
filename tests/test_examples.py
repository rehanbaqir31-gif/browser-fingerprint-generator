import py_compile
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.py"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_compile(path, tmp_path):
    py_compile.compile(str(path), cfile=str(tmp_path / "x.pyc"), doraise=True)


def test_http_example_runs_offline(capsys, monkeypatch):
    import runpy

    monkeypatch.setattr("sys.argv", ["http_requests.py"])
    runpy.run_path(str(next(p for p in EXAMPLES if p.name == "http_requests.py")), run_name="__main__")
    out = capsys.readouterr().out
    assert "User-Agent: Mozilla/5.0" in out and "Accept-Language: en-US" in out
