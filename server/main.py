from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from cmr_agent.graph.pipeline import build_graph


SESSIONS: dict[str, list[str]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global APP_GRAPH
    APP_GRAPH = build_graph()
    yield


app = FastAPI(title='NASA CMR AI Agent', lifespan=lifespan)

async def run_query_stream(user_query: str, session_id: str | None):
    history = SESSIONS.get(session_id, []) if session_id else []
    state = {'user_query': user_query, 'history': history}
    try:
        async for event in APP_GRAPH.astream(state):
            yield (str(event) + '\n').encode('utf-8')
    except Exception as e:
        yield (f"ERROR: {e}\n").encode('utf-8')
    finally:
        if session_id is not None:
            SESSIONS[session_id] = state.get('history', history)

@app.get('/stream')
async def stream(query: str, session_id: str | None = None):
    return StreamingResponse(run_query_stream(query, session_id), media_type='text/event-stream')

@app.get('/query')
async def query(query: str, session_id: str | None = None):
    history = SESSIONS.get(session_id, []) if session_id else []
    result = await APP_GRAPH.ainvoke({'user_query': query, 'history': history})
    if session_id is not None:
        SESSIONS[session_id] = result.get('history', history)
    return result
