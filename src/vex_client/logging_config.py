import logging

from vex_cli.locations import vex_log_directory

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def configure_logging() -> None:
    """Write Vex logs to disk without replacing the launcher's log handlers."""
    log_path = vex_log_directory() / "vex.log"
    logger = logging.getLogger("vex_client")

    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    if logger.level == logging.NOTSET or logger.level > logging.INFO:
        logger.setLevel(logging.INFO)
