import json

import pytest

from fpforge.cli import main


def _run(capsys, *argv):
    code = main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_generate_single_and_many(capsys):
    code, out, _ = _run(capsys, "generate", "--seed", "a", "--country", "US")
    assert code == 0 and json.loads(out)["country"] == "US"
    code, out, _ = _run(capsys, "generate", "-n", "3", "--seed", "a", "--os", "macos", "--compact")
    data = json.loads(out)
    assert code == 0 and len(data) == 3 and all(p["os"] == "macos" for p in data)


def test_generate_is_reproducible(capsys):
    _, a, _ = _run(capsys, "generate", "--seed", "z")
    _, b, _ = _run(capsys, "generate", "--seed", "z")
    assert a == b


def test_generate_to_file(capsys, tmp_path):
    target = tmp_path / "p.json"
    code, out, err = _run(capsys, "generate", "-n", "2", "-o", str(target))
    assert code == 0 and out == "" and "wrote" in err
    assert len(json.loads(target.read_text())) == 2


def test_headers_command(capsys):
    code, out, _ = _run(capsys, "headers", "--seed", "h", "--country", "DE")
    headers = json.loads(out)
    assert code == 0 and "user-agent" in headers and "accept-language" in headers


def test_info_command(capsys):
    code, out, _ = _run(capsys, "info")
    assert code == 0 and "bundled Chrome stable" in out and "windows" in out


def test_no_retarget_flag(capsys):
    _, out, _ = _run(capsys, "generate", "--seed", "r", "--no-retarget")
    assert "chromeFullVersion" not in json.loads(out)["meta"]


def test_rejects_unknown_country_and_impossible_combo(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["generate", "--country", "XX"])
    assert exc.value.code == 2
    capsys.readouterr()
    code, _, err = _run(capsys, "generate", "--os", "linux", "--browser", "safari")
    assert code == 2 and "error" in err
