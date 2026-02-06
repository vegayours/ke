from dataclasses import dataclass
from diskcache import Deque
from config import Config
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T")


class QueueBase(Generic[T]):
    def __init__(self, config: Config, name: str):
        directory = Path(config.document_db_path()) / name
        self.queue = Deque(directory=directory)

    def add(self, item: T):
        self.queue.append(item)

    def next(self) -> T | None:
        try:
            return self.queue.popleft()
        except IndexError:
            return None


@dataclass
class UrlItem:
    url: str
    ignore_cache: bool = False


class UrlQueue(QueueBase[UrlItem]):
    def __init__(self, config: Config):
        super().__init__(config, "url_queue")


@dataclass
class ExtractEntitiesItem:
    url: str
    ignore_cache: bool = False


class ExtractEntitiesQueue(QueueBase[ExtractEntitiesItem]):
    def __init__(self, config: Config):
        super().__init__(config, "extract_entities_queue")


@dataclass
class UpdateGraphItem:
    url: str


class UpdateGraphQueue(QueueBase[UpdateGraphItem]):
    def __init__(self, config: Config):
        super().__init__(config, "update_graph_queue")
