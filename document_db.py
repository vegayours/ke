from diskcache import Index
from config import Config
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DocumentItem:
    url: str
    content: str
    entities: dict | None = None

class DocumentDB:
    def __init__(self, config: Config):
        directory = Path(config.document_db_path()) / "documents"
        self.documents = Index(str(directory))

    def update(self, document: DocumentItem):
        updated = self.get(document.url, {})
        updated.update(document)
        self.documents.update({document.url: updated})

    def get(self, url: str) -> DocumentItem | None:
        return self.documents.get(url)