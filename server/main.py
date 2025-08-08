from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from cmr_agent.graph.pipeline import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    global APP_GRAPH
    APP_GRAPH = build_graph()
    yield


app = FastAPI(title='NASA CMR AI Agent', lifespan=lifespan)

async def run_query_stream(user_query: str):
    state = {'user_query': user_query}
    try:
        async for event in APP_GRAPH.astream(state):
            yield (str(event) + '\n').encode('utf-8')
    except Exception as e:
        yield (f"ERROR: {e}\n").encode('utf-8')

@app.get('/stream')
async def stream(query: str):
    return StreamingResponse(run_query_stream(query), media_type='text/event-stream')

@app.get('/query')
async def query(query: str):
    result = await APP_GRAPH.ainvoke({'user_query': query})
    return result
