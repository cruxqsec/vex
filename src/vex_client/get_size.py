from pathlib import Path


def get_directory_size(path: Path) -> int:
    """Total size in bytes of all files under path (recursive, errors ignored).

    A file vanishing mid-walk, or an unreadable directory, contributes 0
    instead of raising into the UI path.
    """
    total = 0
    try:
        for file in path.rglob("*"):
            try:
                if file.is_file():
                    total += file.stat().st_size
            except OSError:
                continue
    except OSError:
        return total
    return total


def human_readable(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size} {unit}"
        size //= 1024

    return f"{size} PB"