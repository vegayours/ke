import asyncio
import signal
import sys
import argparse
import time
from crawl4ai import AsyncWebCrawler
from config import Config
from queues import UrlQueue, UrlItem
from document_db import DocumentDB, DocumentItem
from logger import get_logger, setup_logging
from entity_extractor import EntityExtractor

logger = get_logger(__name__)

class WorkerBase:
    def __init__(self, name: str, config: Config, check_period_seconds: int):
        self.name = name
        self.config = config
        self.running = True
        self.document_db = DocumentDB(config)
        self.check_period_seconds = check_period_seconds
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

    def handle_exit(self, signum, frame):
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False

    async def loop(self) -> bool:
        raise NotImplementedError

    async def start(self):
        logger.info(f"{self.name} started. Press Ctrl+C to stop.")

        while self.running:
            processed = await self.loop(); 

            if not processed:
                await asyncio.sleep(self.check_period_seconds)

        logger.info(f"{self.name} stopped.")

class UrlWorker(WorkerBase):
    def __init__(self, config: Config):
        super().__init__("URL Worker", config, config.crawl_check_period_seconds())
        self.url_queue = UrlQueue(config)

    async def loop(self) -> bool:
        url_item = self.url_queue.next()
        
        if url_item:
            if not url_item.ignore_cache:
                doc_item = self.document_db.get(url_item.url)
                if doc_item:
                    logger.info(f"URL {url_item.url} already processed. Skipping.")
                    return True

            logger.info(f"Processing URL: {url_item.url}")
            try:
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=url_item.url)
                if result.success:
                    doc_item = DocumentItem(
                        url=url_item.url,
                        content=str(result.markdown)
                    )
                    self.document_db.update(doc_item)
                    logger.info(f"Successfully processed and stored: {url_item.url}")
                else:
                    logger.error(f"Failed to crawl {url_item.url}: {result.error_message}")
            except Exception as e:
                logger.error(f"Error processing {url_item.url}: {e}")
            return True
        else:
            return False
        
class EntityExtractorWorker(WorkerBase):
    def __init__(self, config: Config):
        super().__init__("Entity Extractor Worker", config, config.crawl_check_period_seconds())
        self.extract_entities_queue = ExtractEntitiesQueue(config)
        self.entity_extractor = EntityExtractor(config)

    async def loop(self) -> bool:
        extract_entities_item = self.extract_entities_queue.next()
        
        if extract_entities_item:
            doc_item = self.document_db.get(extract_entities_item.url)

            if not doc_item:
                logger.error(f"Document {extract_entities_item.url} not found.")
                return True

            if not extract_entities_item.ignore_cache:
                if doc_item.entities:
                    logger.info(f"Document {extract_entities_item.url} already processed. Skipping.")
                    return True

            logger.info(f"Extracting entities from document: {extract_entities_item.url}")

            try:
                entities = self.entity_extractor.extract_entities(doc_item)
                doc_item.entities = entities
                self.document_db.update(doc_item)
                logger.info(f"Successfully extracted entities from: {extract_entities_item.url}")
            except Exception as e:
                logger.error(f"Error extracting entities from {extract_entities_item.url}: {e}")
            return True
        else:
            return False

def main():
    parser = argparse.ArgumentParser(description="Knowledge Engine Worker")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    args = parser.parse_args()

    setup_logging()
    config = Config(args.config)
    url_worker = UrlWorker(config)
    entity_extractor_worker = EntityExtractorWorker(config)
    
    try:
        asyncio.run(url_worker.start())
        asyncio.run(entity_extractor_worker.start())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
