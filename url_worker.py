import asyncio
import signal
import sys
import argparse
import time
from crawl4ai import AsyncWebCrawler
from config import Config
from url_queue import UrlQueue, UrlItem
from document_db import DocumentDB, DocumentItem
from logger import get_logger, setup_logging

logger = get_logger(__name__)

class UrlWorker:
    def __init__(self, config: Config):
        self.config = config
        self.url_queue = UrlQueue(config)
        self.document_db = DocumentDB(config)
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

    def handle_exit(self, signum, frame):
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False

    async def start(self):
        logger.info("URL Worker started. Press Ctrl+C to stop.")
        
        async with AsyncWebCrawler() as crawler:
            while self.running:
                url_item = self.url_queue.next()
                
                if url_item:
                    logger.info(f"Processing URL: {url_item.url}")
                    try:
                        result = await crawler.arun(url=url_item.url)
                        if result.success:
                            doc_item = DocumentItem(
                                url=url_item.url,
                                content=result.markdown
                            )
                            self.document_db.update(doc_item)
                            logger.info(f"Successfully processed and stored: {url_item.url}")
                        else:
                            logger.error(f"Failed to crawl {url_item.url}: {result.error_message}")
                    except Exception as e:
                        logger.error(f"Error processing {url_item.url}: {e}")
                else:
                    # No items in queue, sleep for a bit
                    await asyncio.sleep(1)
        
        logger.info("URL Worker stopped.")

def main():
    parser = argparse.ArgumentParser(description="Knowledge Engine URL Worker")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    args = parser.parse_args()

    setup_logging()
    config = Config(args.config)
    worker = UrlWorker(config)
    
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
