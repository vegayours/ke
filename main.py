import argparse
import asyncio
import os
import signal
from worker import worker_main
from config import Config
from document_db import DocumentDB
from queues import UrlQueue, UrlItem
from logger import get_logger, setup_logging
from graph_db import GraphDB

logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 5


async def cli_main(args, config: Config, shutdown_event: asyncio.Event):
    url_queue = UrlQueue(config)
    document_db = DocumentDB(config)
    graph_db = GraphDB(config, read_only=True)

    if args.url:
        logger.info(f"Crawling and processing {args.url}")
        url_queue.add(UrlItem(url=args.url, ignore_cache=args.ignore_cache))
        args.document = args.url

    if args.document:
        logger.info(f"Showing document {args.document}")
        while not shutdown_event.is_set():
            doc_item = document_db.get(args.document)
            if doc_item and doc_item.entities:
                logger.info(f"Document: {doc_item.url}\nEntities: {doc_item.entities}")
                break
            else:
                logger.info(
                    f"Document {args.document} not found or entities not extracted yet, will retry"
                )
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(), timeout=POLL_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                pass

        if shutdown_event.is_set():
            return

    if args.list_entities:
        label = args.list_entities if isinstance(args.list_entities, str) else None
        entities = graph_db.list_entities(label)
        logger.info(f"\nEntities (filter: {label}):")
        for ent in entities:
            logger.info(f"- {ent['name']} ({ent['label']})")

    if args.list_relations:
        relations = graph_db.list_relations(args.list_relations, args.relation_type)
        logger.info(
            f"\nRelations for '{args.list_relations}' (filter: {args.relation_type}):"
        )
        for rel in relations:
            logger.info(f"- {rel['source']} --[{rel['relation']}]--> {rel['target']}")


def parse_args():
    parser = argparse.ArgumentParser(description="Knowledge Engine")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    parser.add_argument("--url", "-u", help="URL to crawl")
    parser.add_argument(
        "--ignore-cache",
        "-i",
        default=False,
        action="store_true",
        help="Crawl ignoring cache",
    )

    parser.add_argument("--document", "-d", help="Document to show")
    parser.add_argument(
        "--list-entities",
        "-le",
        nargs="?",
        const=True,
        help="List all entities (with optional label filter)",
    )
    parser.add_argument(
        "--list-relations", "-lr", help="List all relations for a given entity"
    )
    parser.add_argument(
        "--relation-type", "-rt", help="Optional filter for --list-relations"
    )
    return parser.parse_args()


async def async_main(args, config: Config):
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    def request_shutdown(signum, frame=None):
        logger.info(f"Received signal {signum}. Triggering shutdown...")
        loop.call_soon_threadsafe(shutdown_event.set)

    if os.name == "nt":
        signal.signal(signal.SIGINT, request_shutdown)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, request_shutdown)
    else:
        loop.add_signal_handler(signal.SIGINT, request_shutdown, signal.SIGINT)
        loop.add_signal_handler(signal.SIGTERM, request_shutdown, signal.SIGTERM)

    logger.info("Starting workers concurrently. Press Ctrl+C to stop.")
    await asyncio.gather(
        worker_main(config, shutdown_event),
        cli_main(args, config, shutdown_event),
    )


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    config = Config(args.config)
    asyncio.run(async_main(args, config))
