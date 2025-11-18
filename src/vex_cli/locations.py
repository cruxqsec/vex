from pathlib import Path
from platformdirs import user_data_dir

def vex_data_directory() -> Path:
    """Main Vex directory where all data is stored."""
    vex_data_dir: Path = Path(user_data_dir("vex"))
    vex_data_dir.mkdir(exist_ok=True)
    return vex_data_dir

def vex_projects_directory() -> Path:
    """Directory where all projects are stored."""
    vex_projects_dir: Path = vex_data_directory() / "projects"
    vex_projects_dir.mkdir(exist_ok=True)
    return vex_projects_dir


def vex_log_directory() -> Path:
    """Directory where logs are stored."""
    vex_log_dir: Path = vex_data_directory() / "logs"
    vex_log_dir.mkdir(exist_ok=True)
    return vex_log_dir

def vex_projects_db_path() -> Path:
    """The path to projects.db"""
    vex_projects_db_path: Path = vex_data_directory() / "projects.db"
    return vex_projects_db_path


