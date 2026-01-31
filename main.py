import argparse
from config import Config
from document_db import DocumentDB, DocumentItem
from url_queue import UrlQueue, UrlItem
from logger import get_logger, setup_logging

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Knowledge Engine")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    args = parser.parse_args()

    setup_logging()
    config = Config(args.config)
    url_queue = UrlQueue(config)
    document_db = DocumentDB(config)

    logger.info("Hello from knowledge engine!")

    # Basic url queue test
    logger.info("Basic url queue test")
    url_queue.add(UrlItem(url="https://example.com"))

    logger.info(url_queue.next())
    logger.info(url_queue.next())

    #Basic document db test
    logger.info("Basic document db test")
    document_db.update(DocumentItem(url="https://example.com", content="Hello world"))
    logger.info(document_db.get("https://example.com"))
    logger.info(document_db.get("https://example1.com"))

if __name__ == "__main__":
    main()
