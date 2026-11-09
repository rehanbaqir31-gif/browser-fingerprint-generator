import json
import zipfile

from fpforge._paths import DATA_DIR


def test_all_bundled_data_files_are_present_and_parse():
    for name in ("fingerprint-network-definition.zip", "header-network-definition.zip",
                 "input-network-definition.zip"):
        with zipfile.ZipFile(DATA_DIR / name) as z:
            nodes = json.loads(z.read(z.namelist()[0]))["nodes"]
            assert nodes and all({"name", "parentNames", "conditionalProbabilities"} <= set(n) for n in nodes)
    assert isinstance(json.loads((DATA_DIR / "headers-order.json").read_text()), dict)
    assert isinstance(json.loads((DATA_DIR / "browser-helper-file.json").read_text()), list)
    assert json.loads((DATA_DIR / "chrome-stable.json").read_text())["version"]


def test_fingerprint_network_has_the_expected_nodes(generator):
    names = set(generator.network.by_name)
    assert {"userAgent", "userAgentData", "screen", "videoCard", "fonts", "hardwareConcurrency",
            "deviceMemory", "pluginsData", "battery", "multimediaDevices", "platform"} <= names
