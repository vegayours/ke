import argparse
import time
from config import Config
from document_db import DocumentDB, DocumentItem
from entity_extractor import EntityExtractor
from url_queue import UrlQueue, UrlItem
from logger import get_logger, setup_logging

logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 5

def main():
    parser = argparse.ArgumentParser(description="Knowledge Engine")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    parser.add_argument(
        '--url', '-u',
        help="URL to crawl"
    )
    parser.add_argument(
        '--ignore-cache', '-i',
        default=False,
        action='store_true',
        help="Crawl ignoring cache"
    )

    parser.add_argument(
        '--document', '-d',
        help="Document to show"
    )
    args = parser.parse_args()

    setup_logging()
    config = Config(args.config)
    url_queue = UrlQueue(config)
    document_db = DocumentDB(config)
    entity_extractor = EntityExtractor(config)

    logger.info("Hello from knowledge engine!")

    if args.url:
        logger.info(f"Crawling {args.url}")
        url_queue.add(UrlItem(url=args.url, ignore_cache=args.ignore_cache))
        args.document = args.url

    
    if args.document:
        logger.info(f"Showing document {args.document}")
        while True:
            doc_item = document_db.get(args.document)
            if doc_item:
                entities = entity_extractor.extract_entities(doc_item)
                logger.info(f"Document: {doc_item.url}\nEntities: {entities}")
                break
            else:
                logger.info(f"Document {args.document} not found yet, will retry")
            time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
