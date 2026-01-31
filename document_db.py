from diskcache import Index
from config import Config
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DocumentItem:
    url: str
    content: str

class DocumentDB:
    def __init__(self, config: Config):
        directory = Path(config.document_db_path()) / "documents"
        self.documents = Index(str(directory))

    def update(self, document: DocumentItem):
        self.documents.update({document.url: document})

    def get(self, url: str) -> DocumentItem | None:
        return self.documents.get(url)