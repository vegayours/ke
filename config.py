import sys
from pathlib import Path
import tomllib
from logger import get_logger

logger = get_logger(__name__)

# sample config is config.sample.toml
class Config:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self.load_config()
        self.validate()

    def load_config(self) -> dict:
        path = Path(self.config_path)
        if not path.exists():
            if self.config_path == "config.toml":
                return {}
            logger.error(f"Configuration file not found at {self.config_path}")
            sys.exit(1)

        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            sys.exit(1)

    def validate(self):
        if not self.openrouter_api_key():
            logger.error("OpenRouter API key not found in configuration.")
            sys.exit(1)

        if not self.document_db_path():
            logger.error("Document DB path not found in configuration.")
            sys.exit(1)

        if not self.graph_db_path():
            logger.error("Graph DB path not found in configuration.")
            sys.exit(1)

    def openrouter_api_key(self) -> str:
        return self.config.get("openrouter_api_key")

    def document_db_path(self) -> str:
        return self.config.get("document_db_path")

    def graph_db_path(self) -> str:
        return self.config.get("graph_db_path", "graph_db")

    def crawl_check_period_seconds(self) -> int:
        return self.config.get("crawl_check_period_seconds", 10)

    def entity_extractor_model(self) -> str:
        return self.config.get("entity_extractor_model", "google/gemini-2.5-flash-lite")
    