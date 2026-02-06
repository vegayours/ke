# ke

Quickstart
1. Create and activate a virtualenv.
2. Install dependencies.
3. Add a `config.toml` (see `config.sample.toml`).
4. Run `main.py`.

Example:
```bash
python -m venv .venv
source .venv/bin/activate
pip install uv
uv pip install -e .
cp config.sample.toml config.toml
python main.py --url https://example.com
```
