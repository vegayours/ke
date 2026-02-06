from diskcache import Index
from config import Config
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class DocumentItem:
    url: str
    content: str | None = None
    entities: dict | None = None

    def __or__(self, other):
        return self.__class__(**asdict(self) | asdict(other))


class DocumentDB:
    def __init__(self, config: Config):
        directory = Path(config.document_db_path()) / "documents"
        self.documents = Index(str(directory))

    def update(self, document: DocumentItem):
        updated = self.get(document.url) or DocumentItem(url=document.url)
        updated = updated | document
        self.documents.update({document.url: updated})

    def get(self, url: str) -> DocumentItem | None:
        return self.documents.get(url)
