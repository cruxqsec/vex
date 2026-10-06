import pytest
from unittest.mock import patch

from vex_cli.locations import (
    vex_data_directory,
    vex_log_directory,
    vex_projects_directory,
    vex_tree_sitter_directory,
)


@pytest.fixture(autouse=True)
def isolated_vex_data_dir(tmp_path):
    """Route every vex data directory into tmp_path.

    vex_*_directory() are lru_cached; if a cache was primed before a test's
    user_data_dir patch it wins and the test writes into the real user data
    directory (this polluted ~/.local/share/vex/vex.pid once). Clear the
    caches with the patch active so each test gets a fresh tmp_path root,
    and clear again after so cross-test cache leakage is impossible.
    """
    caches = (
        vex_data_directory,
        vex_projects_directory,
        vex_log_directory,
        vex_tree_sitter_directory,
    )

    def _clear_all() -> None:
        for cache in caches:
            cache.cache_clear()

    with patch(
        "vex_cli.locations.user_data_dir", return_value=str(tmp_path / "vex")
    ):
        _clear_all()
        yield
        _clear_all()