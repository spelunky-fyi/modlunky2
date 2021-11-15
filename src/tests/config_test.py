import json

from modlunky2.config import Config


def test_from_file_nonexistent(tmp_path):
    file_name = tmp_path / "config_test_from_file_nonexistent.json"
    # Just test that this works
    Config.from_path(config_path=file_name)


def test_from_file_json(tmp_path):
    file_name = tmp_path / "config_test_from_file_json.json"
    data = {"playlunky-version": "latest"}
    with file_name.open("w", encoding="utf-8") as config_file:
        json.dump(data, config_file)

    config = Config.from_path(config_path=file_name)
    assert config.playlunky_version == "latest"
