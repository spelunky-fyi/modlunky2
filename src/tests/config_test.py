import json

from modlunky2.config import Config


def test_from_file_none():
    # Just test that this succeeds
    Config.from_path()


def test_from_file_json(tmp_path):
    file_name = tmp_path / "config_test_from_file.json"
    data = {"playlunky-version": "latest"}
    with file_name.open("w", encoding="utf-8") as config_file:
        json.dump(data, config_file)

    config = Config.from_path(config_path=file_name)
    assert config.playlunky_version == "latest"
