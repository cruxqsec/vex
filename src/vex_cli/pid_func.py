import errno
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import psutil

from vex_cli.locations import vex_lock_file, vex_server_metadata_file
from vex_cli.models.pydantic import ServerMetaData, VexServerInfo

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def write_metadata_file(data: ServerMetaData) -> None:
    """Publish complete metadata without exposing a partially written file."""
    metadata_file = vex_server_metadata_file()
    temporary = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=metadata_file.parent,
        prefix=f".{metadata_file.name}.",
        delete=False,
    )
    temporary_path = Path(temporary.name)

    try:
        with temporary:
            temporary.write(data.model_dump_json(indent=2))

        os.replace(temporary_path, metadata_file)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_metadata_file() -> ServerMetaData:
    """Read server metadata; this does not establish liveness."""
    return ServerMetaData.model_validate_json(
        vex_server_metadata_file().read_text(encoding="utf-8")
    )


def _acquire_file_lock(fd: int) -> None:
    """Acquire the non-blocking singleton lock.

    Locks byte zero on Windows and the whole file on POSIX.
    """
    if sys.platform == "win32":
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


@asynccontextmanager
async def lock_file_check(server_info: VexServerInfo):
    """Hold the singleton lock and publish server metadata.

    The lock descriptor remains open for the context's lifetime.
    Both files remain on disk after exit; file existence is not liveness.
    """
    fd = os.open(vex_lock_file(), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            _acquire_file_lock(fd)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise RuntimeError("vex-cli is already running.") from exc
            raise

        # we get the creation time of the process
        # so we can compare PID AND create time
        # in case of PID reuse
        process = psutil.Process()

        data = ServerMetaData(
            pid=os.getpid(),
            create_time=process.create_time(),
            host=str(server_info.server_address),
            proxy_port=server_info.proxy_port,
            api_port=server_info.api_port,
        )
        write_metadata_file(data)
        yield
    finally:
        # we just close the file descriptor so we release the lock
        # but we leave the file intentionally staleness is decided by holding the lock,
        # not by inspecting the pid and the kernel has already released the lock.
        os.close(fd)
