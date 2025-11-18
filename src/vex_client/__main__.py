from vex_client.app import VexApp
from vex_cli.locations import vex_log_directory

import logging
logger = logging.getLogger(__name__)

def main():
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(vex_log_directory()/'vex.log')]
        )  
        app = VexApp()
        app.run()
    except Exception as e:
        logger.error(f"Unexpected exception in client: {e}")
        print("An error occurred. Please check the logs and open an issue in Github.")

if __name__ == "__main__":
    main()
