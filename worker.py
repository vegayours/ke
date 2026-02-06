import asyncio
import signal
import argparse
from crawl4ai import AsyncWebCrawler
from config import Config
from queues import (
    UrlQueue,
    UrlItem,
    ExtractEntitiesQueue,
    ExtractEntitiesItem,
    UpdateGraphQueue,
    UpdateGraphItem,
)
from document_db import DocumentDB, DocumentItem
from logger import get_logger, setup_logging
from entity_extractor import EntityExtractor
from graph_db import GraphDB
from typing import Generic, TypeVar

QueueType = TypeVar("QueueType")
QueueItemType = TypeVar("QueueItemType")

logger = get_logger(__name__)
RETRY_DELAY_SECONDS = 10


class WorkerBase(Generic[QueueType, QueueItemType]):
    def __init__(
        self, name: str, config: Config, shutdown_event: asyncio.Event, queue: QueueType
    ):
        self.name = name
        self.logger = get_logger(self.name)
        self.config = config
        self.document_db = DocumentDB(config)
        self.shutdown_event = shutdown_event
        self.queue = queue

    async def process(self, item: QueueItemType):
        raise NotImplementedError

    async def retry_after_delay(self, item: QueueItemType):
        try:
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            self.queue.add(item)
            self.logger.info("Item re-added to queue for retry.")
        except Exception as e:
            self.logger.error(f"Error retrying item: {e}")

    async def start(self):
        self.logger.info("Worker started.")

        while not self.shutdown_event.is_set():
            item = self.queue.next()

            if item:
                try:
                    await self.process(item)
                except Exception as e:
                    self.logger.error(f"Error processing item: {e}")
                    asyncio.create_task(self.retry_after_delay(item))
            else:
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.config.queue_check_period_seconds(),
                    )
                except asyncio.TimeoutError:
                    pass

        logger.info("Worker stopped.")


class UrlWorker(WorkerBase[UrlQueue, UrlItem]):
    def __init__(self, config: Config, shutdown_event: asyncio.Event):
        super().__init__("URL Worker", config, shutdown_event, UrlQueue(config))
        self.entity_extractor_queue = ExtractEntitiesQueue(config)

    async def process(self, item: UrlItem):
        if not item.ignore_cache:
            doc_item = self.document_db.get(item.url)
            if doc_item:
                self.logger.info(f"URL {item.url} already processed. Skipping.")
                if not doc_item.entities:
                    self.entity_extractor_queue.add(ExtractEntitiesItem(url=item.url))
                return

        self.logger.info(f"Processing URL: {item.url}")
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=item.url)
            if result.success:
                doc_item = DocumentItem(url=item.url, content=str(result.markdown))
                self.document_db.update(doc_item)
                self.entity_extractor_queue.add(ExtractEntitiesItem(url=item.url))
                logger.info(f"Successfully processed and stored: {item.url}")
            else:
                raise Exception(f"Failed to crawl {item.url}: {result.error_message}")


class EntityExtractorWorker(WorkerBase[ExtractEntitiesQueue, ExtractEntitiesItem]):
    def __init__(self, config: Config, shutdown_event: asyncio.Event):
        super().__init__(
            "Entity Extractor Worker",
            config,
            shutdown_event,
            ExtractEntitiesQueue(config),
        )
        self.entity_extractor = EntityExtractor(config)
        self.update_graph_queue = UpdateGraphQueue(config)

    async def process(self, item: ExtractEntitiesItem):
        if not item.ignore_cache:
            doc_item = self.document_db.get(item.url)
            if not doc_item:
                self.logger.error(f"Document {item.url} not found. Skipping.")
                return

            if not item.ignore_cache:
                if doc_item.entities:
                    self.logger.info(
                        f"Document {item.url} already processed. Skipping."
                    )
                    return

        self.logger.info(f"Extracting entities from document: {item.url}")
        entities = self.entity_extractor.extract_entities(doc_item)
        doc_item.entities = entities
        self.document_db.update(doc_item)
        self.update_graph_queue.add(UpdateGraphItem(url=item.url))
        self.logger.info(f"Successfully extracted entities from: {item.url}")


class GraphWorker(WorkerBase[UpdateGraphQueue, UpdateGraphItem]):
    def __init__(self, config: Config, shutdown_event: asyncio.Event):
        super().__init__(
            "Graph Worker", config, shutdown_event, UpdateGraphQueue(config)
        )
        self.graph_db = GraphDB(config)

    async def process(self, item: UpdateGraphItem):
        if not item.ignore_cache:
            doc_item = self.document_db.get(item.url)
            if not doc_item or not doc_item.entities:
                self.logger.error(
                    f"Document {item.url} not found or no entities found. Skipping."
                )
                return

        self.logger.info(f"Updating graph for document: {item.url}")

        self.graph_db.update_graph(doc_item.entities)
        self.logger.info(f"Successfully updated graph for: {item.url}")


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
