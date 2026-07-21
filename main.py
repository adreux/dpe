import logging
import os

import dotenv

from src.logger import setup_logging

dotenv.load_dotenv()

setup_logging()

logger = logging.getLogger(__name__)

key = os.environ.get("fake_key")


def main():
    logger.info("En avant! Nouveau projet 🎉")


if __name__ == "__main__":
    main()
