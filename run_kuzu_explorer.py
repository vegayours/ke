#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from config import Config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Kuzu DB Explorer against graph DB from config."
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config.toml (default: config.toml next to this script).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Local port to expose Kuzu Explorer (default: 8000).",
    )
    args = parser.parse_args()

    config = Config(args.config)
    graph_db_path_raw = config.graph_db_path()
    if not isinstance(graph_db_path_raw, str) or not graph_db_path_raw.strip():
        raise SystemExit(
            "Invalid graph_db_path in config.toml (expected non-empty string)."
        )
    graph_db_path = (Path(args.config).parent / graph_db_path_raw).parent.resolve()

    cmd = [
        "docker",
        "run",
        "-p",
        f"{args.port}:8000",
        "-v",
        f"{graph_db_path}/:/database",
        "-e",
        "KUZU_FILE=graph_db",
        "--rm",
        "kuzudb/explorer:latest",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
