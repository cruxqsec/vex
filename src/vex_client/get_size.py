from pathlib import Path

def get_directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.glob("*") if file.is_file())

def human_readable(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size} {unit}"
        size //= 1024
    
    return ""
