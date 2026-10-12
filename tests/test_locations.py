import pytest

from vex_cli.locations import (
    vex_data_directory,
    vex_log_directory,
    vex_pid_file,
    vex_projects_db_path,
    vex_projects_directory,
)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, mocker):
    root = tmp_path / "vex"
    mocker.patch("vex_cli.locations.user_data_dir", return_value=str(root))
    return root


def test_data_directory_is_created():
    result = vex_data_directory()

    assert result.is_dir()
    assert result.name == "vex"


@pytest.mark.parametrize(
    ("func", "name"),
    [(vex_projects_directory, "projects"), (vex_log_directory, "logs")],
)
def test_subdirectories_are_created_inside_data_directory(func, name):
    result = func()

    assert result == vex_data_directory() / name
    assert result.is_dir()


def test_pid_file_path_is_inside_data_directory():
    assert vex_pid_file() == vex_data_directory() / "vex.pid"


def test_projects_db_path_is_inside_data_directory():
    assert vex_projects_db_path() == vex_data_directory() / "projects.db"
