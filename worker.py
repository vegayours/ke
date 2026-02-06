import asyncio
import signal
import argparse
from crawl4ai import AsyncWebCrawler
from config import Config
from queues import (
    UrlQueue,
    ExtractEntitiesQueue,
    ExtractEntitiesItem,
    UpdateGraphQueue,
    UpdateGraphItem,
)
from document_db import DocumentDB, DocumentItem
from logger import get_logger, setup_logging
from entity_extractor import EntityExtractor
from graph_db import GraphDB

logger = get_logger(__name__)
RETRY_DELAY_SECONDS = 10


class WorkerBase:
    def __init__(
        self,
        name: str,
        config: Config,
        check_period_seconds: int,
        shutdown_event: asyncio.Event,
    ):
        self.name = name
        self.config = config
        self.document_db = DocumentDB(config)
        self.check_period_seconds = check_period_seconds
        self.shutdown_event = shutdown_event

    async def loop(self) -> bool:
        raise NotImplementedError

    async def retry_after_delay(self, item, queue):
        await asyncio.sleep(RETRY_DELAY_SECONDS)
        queue.add(item)
        logger.info(f"{self.name}: Item re-added to queue for retry.")

    async def start(self):
        logger.info(f"{self.name} started.")

        while not self.shutdown_event.is_set():
            processed = await self.loop()

            if not processed:
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=self.check_period_seconds
                    )
                except asyncio.TimeoutError:
                    pass

        logger.info(f"{self.name} stopped.")


class UrlWorker(WorkerBase):
    def __init__(self, config: Config, shutdown_event: asyncio.Event):
        super().__init__(
            "URL Worker", config, config.crawl_check_period_seconds(), shutdown_event
        )
        self.url_queue = UrlQueue(config)
        self.entity_extractor_queue = ExtractEntitiesQueue(config)

    async def loop(self) -> bool:
        url_item = self.url_queue.next()

        if url_item:
            if not url_item.ignore_cache:
                doc_item = self.document_db.get(url_item.url)
                if doc_item:
                    logger.info(f"URL {url_item.url} already processed. Skipping.")
                    if not doc_item.entities:
                        self.entity_extractor_queue.add(
                            ExtractEntitiesItem(url=url_item.url)
                        )
                    return True

            logger.info(f"Processing URL: {url_item.url}")
            try:
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=url_item.url)
                if result.success:
                    doc_item = DocumentItem(
                        url=url_item.url, content=str(result.markdown)
                    )
                    self.document_db.update(doc_item)
                    self.entity_extractor_queue.add(
                        ExtractEntitiesItem(url=url_item.url)
                    )
                    logger.info(f"Successfully processed and stored: {url_item.url}")
                else:
                    logger.error(
                        f"Failed to crawl {url_item.url}: {result.error_message}"
                    )
                    asyncio.create_task(
                        self.retry_after_delay(url_item, self.url_queue)
                    )
            except Exception as e:
                logger.error(f"Error processing {url_item.url}: {e}")
                asyncio.create_task(self.retry_after_delay(url_item, self.url_queue))
            return True
        else:
            return False


class EntityExtractorWorker(WorkerBase):
    def __init__(self, config: Config, shutdown_event: asyncio.Event):
        super().__init__(
            "Entity Extractor Worker",
            config,
            config.crawl_check_period_seconds(),
            shutdown_event,
        )
        self.extract_entities_queue = ExtractEntitiesQueue(config)
        self.entity_extractor = EntityExtractor(config)
        self.update_graph_queue = UpdateGraphQueue(config)

    async def loop(self) -> bool:
        extract_entities_item = self.extract_entities_queue.next()

        if extract_entities_item:
            doc_item = self.document_db.get(extract_entities_item.url)

            if not doc_item:
                logger.error(f"Document {extract_entities_item.url} not found.")
                return True

            if not extract_entities_item.ignore_cache:
                if doc_item.entities:
                    logger.info(
                        f"Document {extract_entities_item.url} already processed. Skipping."
                    )
                    return True

            logger.info(
                f"Extracting entities from document: {extract_entities_item.url}"
            )

            try:
                entities = self.entity_extractor.extract_entities(doc_item)
                doc_item.entities = entities
                self.document_db.update(doc_item)
                self.update_graph_queue.add(
                    UpdateGraphItem(url=extract_entities_item.url)
                )
                logger.info(
                    f"Successfully extracted entities from: {extract_entities_item.url}"
                )
            except Exception as e:
                logger.error(
                    f"Error extracting entities from {extract_entities_item.url}: {e}"
                )
                asyncio.create_task(
                    self.retry_after_delay(
                        extract_entities_item, self.extract_entities_queue
                    )
                )
            return True
        else:
            return False


class GraphWorker(WorkerBase):
    def __init__(self, config: Config, shutdown_event: asyncio.Event):
        super().__init__(
            "Graph Worker", config, config.crawl_check_period_seconds(), shutdown_event
        )
        self.update_graph_queue = UpdateGraphQueue(config)
        self.graph_db = GraphDB(config)

    async def loop(self) -> bool:
        update_item = self.update_graph_queue.next()
        if update_item:
            doc_item = self.document_db.get(update_item.url)
            if not doc_item or not doc_item.entities:
                logger.error(f"No entities found for document {update_item.url}")
                return True

            logger.info(f"Updating graph for document: {update_item.url}")
            try:
                self.graph_db.update_graph(doc_item.entities)
                logger.info(f"Successfully updated graph for: {update_item.url}")
            except Exception as e:
                logger.error(f"Error updating graph for {update_item.url}: {e}")
                asyncio.create_task(
                    self.retry_after_delay(update_item, self.update_graph_queue)
                )
            return True
        else:
            return False


async def async_main(config_path: str):
    setup_logging()
    config = Config(config_path)
    shutdown_event = asyncio.Event()

    def handle_exit(signum, frame):
        logger.info(f"Received signal {signum}. Triggering shutdown...")
        shutdown_event.set()

    # Register signals
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    url_worker = UrlWorker(config, shutdown_event)
    entity_extractor_worker = EntityExtractorWorker(config, shutdown_event)
    graph_worker = GraphWorker(config, shutdown_event)

    logger.info("Starting workers concurrently. Press Ctrl+C to stop.")
    await asyncio.gather(
        url_worker.start(), entity_extractor_worker.start(), graph_worker.start()
    )


def main():
    parser = argparse.ArgumentParser(description="Knowledge Engine Worker")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(async_main(args.config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
