# GEMINI.md: Knowledge Engine (ke)

## Project Overview

This project, "Knowledge Engine" (ke), is a Python-based application designed to build a knowledge graph from web pages. It operates as a data processing pipeline that crawls specified URLs, extracts entities and their relationships using a Large Language Model (LLM), and stores them in a graph database.

The architecture consists of three main asynchronous workers that communicate through persistent, on-disk queues:

1.  **URL Worker**: Fetches URLs from a queue, crawls the web page content using `crawl4ai`, and stores the result in a document database.
2.  **Entity Extractor Worker**: Takes crawled content, uses an LLM via `openrouter` (e.g., `google/gemini-2.5-flash-lite`) to identify and extract entities and relationships, and updates the document with this information.
3.  **Graph Worker**: Processes the extracted entities and upserts them as nodes and edges into a `kuzu` graph database, effectively building the knowledge graph.

## Key Technologies

*   **Programming Language:** Python
*   **Web Crawling:** `crawl4ai`
*   **LLM Interaction:** `openrouter`
*   **Graph Database:** `kuzu`
*   **Queues & Document Storage:** `diskcache`

## Building and Running

### 1. Setup

**a. Configuration:**

Create a `config.toml` file in the root directory by copying the sample configuration:

```bash
cp config.sample.toml config.toml
```

Edit `config.toml` and add your `openrouter_api_key`:

```toml
openrouter_api_key = "your-api-key-here"
# Other configurations can be left as default
```

**b. Dependencies:**

It is recommended to use a virtual environment. The project uses `uv` for package management.

```bash
# First time setup
python -m venv .venv
source .venv/bin/activate
pip install uv
uv pip install -r requirements.txt
```

*Note: As there is no `requirements.txt` file, one would need to be generated from `pyproject.toml`, for example by running `uv pip freeze > requirements.txt` and then `uv pip install -r requirements.txt`. For simplicity, `uv pip install -e .` should also work if the project is set up for it.*

### 2. Running the Workers

The workers process the queues in the background. To start them, run:

```bash
python worker.py
```

The workers will now be running and waiting for tasks.

### 3. Adding a URL to Process

To add a web page to the knowledge graph, use `main.py` with the `--url` argument:

```bash
python main.py --url https://en.wikipedia.org/wiki/Gemini_(chatbot)
```

This will add the URL to the `UrlQueue`, and the `UrlWorker` will pick it up for processing.

### 4. Checking the Results

To check if a document has been processed and see the extracted entities, use the `--document` argument:

```bash
python main.py --document https://en.wikipedia.org/wiki/Gemini_(chatbot)
```

This command will poll the document database and print the entities once they have been extracted and stored.

## Development Conventions

*   **Asynchronous Workers:** The core logic is built around `asyncio` and concurrent workers.
*   **Queue-Based Communication:** Workers are decoupled and communicate via persistent queues (`diskcache.Deque`), allowing for resilient and scalable processing.
*   **Centralized Configuration:** All configuration is managed through the `Config` class, which reads from a `config.toml` file.
*   **Structured Logging:** The application uses a centralized logging setup to provide clear and consistent logs.
*   **Dataclasses:** Data structures for queue items and document items are clearly defined using Python's `dataclasses`.
