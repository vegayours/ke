import argparse
from config import Config
from document_db import DocumentDB, DocumentItem
from url_queue import UrlQueue, UrlItem

def main():
    parser = argparse.ArgumentParser(description="Knowledge Engine")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    args = parser.parse_args()

    config = Config(args.config)
    url_queue = UrlQueue(config)
    document_db = DocumentDB(config)

    print("Hello from knowledge engine!")

    # Basic url queue test
    print("Basic url queue test")
    url_queue.add(UrlItem(url="https://example.com"))

    print(url_queue.next())
    print(url_queue.next())

    #Basic document db test
    print("Basic document db test")
    document_db.update(DocumentItem(url="https://example.com", content="Hello world"))
    print(document_db.get("https://example.com"))
    print(document_db.get("https://example1.com"))

if __name__ == "__main__":
    main()
