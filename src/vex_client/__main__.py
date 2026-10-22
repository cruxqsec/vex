import logging

from vex_client.app import VexApp

logger = logging.getLogger(__name__)


def main():
    try:
        app = VexApp()
        app.run()
    except Exception:
        logger.exception("Unexpected client error")
        print("An error occurred. Please check the logs and open an issue in Github.")


if __name__ == "__main__":
    main()
