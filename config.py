import sys
from pathlib import Path
import tomllib

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
            print(f"Error: Configuration file not found at {self.config_path}")
            sys.exit(1)

        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    def validate(self):
        if not self.openrouter_api_key():
            print("Error: OpenRouter API key not found in configuration.")
            sys.exit(1)

        if not self.document_db_path():
            print("Error: Document DB path not found in configuration.")
            sys.exit(1)

    def openrouter_api_key(self) -> str:
        return self.config.get("openrouter_api_key")

    def document_db_path(self) -> str:
        return self.config.get("document_db_path")
    