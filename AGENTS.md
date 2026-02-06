# AGENTS.md

This document provides comprehensive, practical context for AI agents working in this repo.

## Architecture Overview
Knowledge Engine (ke) is a Python pipeline that:
1. Crawls web pages (`crawl4ai`)
2. Extracts entities/relations via LLM (`openrouter`)
3. Builds a knowledge graph in Kuzu (`kuzu`)

The system is implemented as three async workers connected by disk-backed queues
(`diskcache`). Data flows forward through the pipeline but can be re-queued on
failure for retry.

## End-to-End Data Flow
1. A URL is added to the `UrlQueue` (CLI via `main.py --url`).
2. `UrlWorker` crawls the page and stores raw content in the `DocumentDB`.
3. `EntityExtractorWorker` reads the document, calls OpenRouter, and writes
   structured entities/relations back to the document.
4. `GraphWorker` reads extracted entities and upserts them into Kuzu.
5. The CLI can list entities/relations or poll document extraction progress.

## Runtime Topology
- All three workers run concurrently in a single process (`worker_main`), driven
  by `asyncio.gather`.
- Each worker loop checks its queue, processes items, and sleeps for
  `queue_check_period_seconds` when idle.
- Errors are logged and the item is re-queued with a fixed delay.

## Storage Model
- **Document DB**: Disk-backed `diskcache.Index` storing `DocumentItem`s by URL.
- **Queues**: Disk-backed `diskcache.Deque` per stage:
  - `url_queue`
  - `extract_entities_queue`
  - `update_graph_queue`
- **Graph DB**: Kuzu database with:
  - Node table `Entity(name STRING, label STRING)`
  - Relationship table `RelatedTo(FROM Entity TO Entity, relation STRING)`

## Key Entry Points
- `main.py` — CLI and orchestrator that starts workers and handles user commands.
- `worker.py` — Implements the three workers and the queue-driven pipeline.

## Important Modules
- `config.py` — Loads and validates `config.toml`.
- `queues.py` — Disk-backed queues and queue item dataclasses.
- `document_db.py` — Disk-backed document storage and merge logic.
- `entity_extractor.py` — OpenRouter prompt + JSON parsing.
- `graph_db.py` — Kuzu schema setup + graph upsert/list helpers.
- `logger.py` — Centralized logging.

## Configuration
You must provide a `config.toml` (see `config.sample.toml`):
- `openrouter_api_key` (required)
- `document_db_path` (required)
- `graph_db_path` (optional, default `graph_db`)
- `queue_check_period_seconds` (optional, default `10`)
- `entity_extractor_model` (optional, default `google/gemini-2.5-flash-lite`)

## Common Commands
Setup (example, assumes `uv` is already installed):
```bash
uv venv
uv sync
```

Setup (example, installs `uv` first):
```bash
pip install uv
uv venv
uv sync
```

Run workers + CLI:
```bash
uv run main.py --url https://example.com
```

Poll an extracted document:
```bash
uv run main.py --document https://example.com
```

List entities or relations:
```bash
uv run main.py --list-entities
uv run main.py --list-relations "Entity Name"
```

## Operational Notes
- `main.py` starts all workers concurrently and also executes CLI actions.
- URL caching can be bypassed with `--ignore-cache`.
- Entity extraction uses deterministic LLM settings (`temperature=0.0`).
- Kuzu schema creation is idempotent; errors are ignored if tables exist.

## Development Notes
- Python target version is 3.14 (`pyproject.toml`).
- All persistent state is on disk; no external services besides OpenRouter.
