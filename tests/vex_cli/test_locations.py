import pytest

from vex_cli.locations import (
    vex_data_directory,
    vex_lock_file,
    vex_log_directory,
    vex_projects_db_path,
    vex_projects_directory,
    vex_server_metadata_file,
    vex_tree_sitter_directory,
)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, mocker):
    root = tmp_path / "vex"
    mocker.patch("vex_cli.locations.user_data_dir", return_value=str(root))
    directories = (
        vex_data_directory,
        vex_projects_directory,
        vex_log_directory,
        vex_tree_sitter_directory,
    )
    for directory in directories:
        directory.cache_clear()
    yield root
    for directory in directories:
        directory.cache_clear()


def test_data_directory_is_created():
    result = vex_data_directory()

    assert result.is_dir()
    assert result.name == "vex"


@pytest.mark.parametrize(
    ("func", "name"),
    [
        (vex_projects_directory, "projects"),
        (vex_log_directory, "logs"),
        (vex_tree_sitter_directory, "tree_sitter"),
    ],
)
def test_subdirectories_are_created_inside_data_directory(func, name):
    result = func()

    assert result == vex_data_directory() / name
    assert result.is_dir()


def test_server_files_are_inside_data_directory():
    assert vex_lock_file() == vex_data_directory() / "vex.lock"
    assert vex_server_metadata_file() == vex_data_directory() / "vex-server.json"


def test_projects_db_path_is_inside_data_directory():
    assert vex_projects_db_path() == vex_data_directory() / "projects.db"
