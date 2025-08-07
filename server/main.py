from __future__ import annotations
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from cmr_agent.graph.pipeline import build_graph

app = FastAPI(title='NASA CMR AI Agent')

@app.on_event('startup')
def on_startup():
    global APP_GRAPH
    APP_GRAPH = build_graph()

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
    graph = build_graph()
    result = await graph.ainvoke({'user_query': query})
    return result
