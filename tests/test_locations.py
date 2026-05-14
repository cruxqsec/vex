from unittest.mock import patch

import pytest

from vex_cli.locations import (
    vex_data_directory,
    vex_log_directory,
    vex_pid_file,
    vex_projects_db_path,
    vex_projects_directory,
)
from vex_cli.pid_func import write_pid_file


@pytest.fixture(autouse=False)
def mock_data_dir(tmp_path):
    with patch("vex_cli.locations.user_data_dir", return_value=str(tmp_path / "vex")):
        yield tmp_path / "vex"


def test_vex_data_directory_creates_dir(tmp_path):
    with patch("vex_cli.locations.user_data_dir", return_value=str(tmp_path / "vex")):
        result = vex_data_directory()
        assert result.exists()
        assert result.is_dir()


def test_vex_data_project_dir_is_created(tmp_path):
    with patch("vex_cli.locations.user_data_dir", return_value=str(tmp_path / "vex")):
        result = vex_projects_directory()
        assert result.exists()
        assert result.is_dir()
        assert (vex_data_directory() / "projects").exists()


def test_vex_data_log_dir_is_created(tmp_path):
    with patch("vex_cli.locations.user_data_dir", return_value=str(tmp_path / "vex")):
        result = vex_log_directory()
        assert result.exists()
        assert result.is_dir()
        assert (vex_data_directory() / "logs").exists()


def test_vex_data_pid_file_is_created(tmp_path):
    with patch("vex_cli.locations.user_data_dir", return_value=str(tmp_path / "vex")):
        pid_file = vex_data_directory() / "vex.pid"
        write_pid_file("127.0.0.1", 8080, 9090, pid_file)

        result = vex_pid_file()
        assert result.exists()
        assert result.is_file()
        assert (vex_data_directory() / "vex.pid").exists()


def test_vex_projects_db_path_is_inside_data_dir(tmp_path):
    with patch("vex_cli.locations.user_data_dir", return_value=str(tmp_path / "vex")):
        result = vex_projects_db_path()
        assert result.name == "projects.db"
        assert result.parent == vex_data_directory()
