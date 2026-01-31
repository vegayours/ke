from dataclasses import dataclass
from diskcache import Deque
from config import Config
from pathlib import Path

@dataclass
class UrlItem:
    url: str
    ignore_cache: bool = False 
    

class UrlQueue:
    def __init__(self, config: Config):
        directory = Path(config.document_db_path()) / "url_queue"
        self.url_queue = Deque(directory=directory)

    def add(self, url: UrlItem):
        self.url_queue.append(url)

    def next(self) -> UrlItem | None:
        try:
            return self.url_queue.popleft()
        except IndexError:
            return None

