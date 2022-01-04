import json

from modlunky2.config import Config


def test_from_path_nonexistent(tmp_path, request):
    file_name = tmp_path / f"config_{request.node.name}.json"
    # Just test that this works
    Config.from_path(config_path=file_name)


def test_from_path_playlunky_version_present(tmp_path, request):
    file_name = tmp_path / f"config_{request.node.name}.json"
    data = {"playlunky-version": "latest"}
    with file_name.open("w", encoding="utf-8") as config_file:
        json.dump(data, config_file)

    config = Config.from_path(config_path=file_name)
    assert config.playlunky_version == "latest"


def test_from_path_install_dir_null(tmp_path, request):
    file_name = tmp_path / f"config_{request.node.name}.json"
    data = {"install-dir": None}
    with file_name.open("w", encoding="utf-8") as config_file:
        json.dump(data, config_file)

    config = Config.from_path(config_path=file_name)
    assert config.install_dir is None


def test_from_path_last_tab_null(tmp_path, request):
    file_name = tmp_path / f"config_{request.node.name}.json"
    data = {"last-tab": None}
    with file_name.open("w", encoding="utf-8") as config_file:
        json.dump(data, config_file)

    config = Config.from_path(config_path=file_name)
    assert config.last_tab is None
