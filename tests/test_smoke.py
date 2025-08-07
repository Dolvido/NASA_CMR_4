import asyncio
import pytest
from cmr_agent.graph.pipeline import build_graph

@pytest.mark.asyncio
async def test_graph_runs():
  graph = build_graph()
  res = await graph.ainvoke({'user_query': 'Find MODIS aerosol datasets 2020 global'})
  assert 'synthesis' in res
