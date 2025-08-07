## NASA CMR AI Agent (LangGraph)

### Overview
An async, multi‑agent LangGraph pipeline that interprets natural‑language queries, validates intent, queries NASA CMR (collections/granules), performs lightweight analysis, retrieves semantic context from a local Chroma vector store, and synthesizes responses. Server exposes `/query` and `/stream` endpoints.

### Quickstart
1) Create and activate a virtual env, then install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

2) Optional LLM keys (for better intent/synthesis). Create `.env`:

```dotenv
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
# For broad discovery, avoid over-restricting provider:
CMR_PROVIDER=ALL
```

3) Run tests:

```powershell
pytest -q
```

4) CLI usage:

```powershell
python cli.py "Find MODIS aerosol datasets 2020 global"
```

5) Start API server:

```powershell
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Endpoints:
- `GET /query?query=...` returns final graph state (JSON)
- `GET /stream?query=...` streams step events (text/event-stream)

### Project structure

```
cmr_agent/
  agents/           # intent, validation, cmr, analysis, synthesis, retrieval
  cmr/              # httpx async client + circuit breaker
  graph/            # LangGraph pipeline assembly
  llm/              # provider router (OpenAI/Anthropic)
  vectordb.py       # Chroma integrations (local persistence)
server/             # FastAPI app
tests/              # pytest smoke
```

### Notes
- CMR search reliability depends on good parameterization. Without LLMs, heuristics infer years and a few regions. Improve by expanding query planning.
- Chroma persistence lives under `vectordb/chroma/` (gitignored). To ingest docs:

```python
from cmr_agent.vectordb import ingest_docs
ingest_docs([{ "id": 1, "text": "GPM IMERG precipitation dataset ..." }])
```

### License
Proprietary / Assessment use only.


